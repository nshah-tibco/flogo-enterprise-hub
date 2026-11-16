"""Business logic of Retail.Policy.API rebuilt in Flogo (worked example: BW AI-plugin RAG -> OpenAI vector store via the
repo-local openAI extension + Agentic AI LLM Client; static resource lookups; subflows with an iterator).

BW6 source (decoded by analyze_bw6.py):
  GET  /api/policy/resources[?type]            static policy list (ParseJSON), uri = retail://<documentType>/<id>
  GET  /api/policy/resources/{id}              one policy by id (+ text)
  GET  /api/policy/resources/read?uri          one policy by uri (+ text)
  POST /api/ingest   {source, documentTypes[], resetCollection}
       seed docs (ParsePolicyDocs) -> normalize (category/uri/tags) -> keep documentTypes -> chunk -> ingest into Weaviate
       (BW ignores resetCollection: ParseIngestRequest is never read)
  POST /api/upload   {fileName, contentBase64, ...}  decode -> one document -> chunk -> ingest
  POST /api/policy/query {question, ...}       Weaviate retrieval + gpt-4.1-mini answer -> question/answer/retrieval/citations/raw/metadata

Flogo design:
  ResolveStore(reset) subflow: list vector stores -> the one named $property[VECTOR_STORE_NAME] (reset: delete + recreate;
  missing: create) -> storeId. AddDocument subflow: write the text to <POLICY_DOCS_DIR>/<fileName> -> upload it into the
  store with its metadata as file attributes (search results carry them, so nothing is inferred from chunk text).
  Ingest runs AddDocument once per document (iterator); query = vectorSearch -> LLM Client answer (gpt-5.5 by default).

Usage: python policy_logic.py <work>/plan.json
       (export FLOGO_DESIGN_CONFIG_FILE=<work>/fda-config.json from extend_fda_catalog.py first)

API key: the openAI extension declares its apiKey field as a plain string, so the designer rejects binding it to a
password (SECRET:) property. OPENAI_API_KEY is therefore a plain-string PLACEHOLDER in the .flogo (no secret in the
file); supply the real key at run time, e.g.  FLOGO_APP_PROPS_ENV=auto OPENAI_API_KEY=sk-... ./RetailPolicyAPI
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic  # noqa: E402

L = Logic(sys.argv[1])
LS, BYID, RD = L.flow("list_policy_resources"), L.flow("get_api_policy_resources_id"), L.flow("read_policy_resource")
ING, UPL, QRY = L.flow("post_api_ingest"), L.flow("post_api_upload"), L.flow("post_api_policy_query")
count = lambda act: f"array.count($activity[{act}].output.matches)"

# ---------------------------------------------------------------- app properties
L.prop("OPENAI_API_KEY", "string", "YOUR_OPENAI_API_KEY")   # placeholder: real key via env at run time (see docstring)
L.prop("OPENAI_API_ENDPOINT_URL", "string", "https://api.openai.com/v1")
L.prop("LLM_PROVIDER", "string", "OpenAI")
L.prop("LLM_MODEL", "string", "gpt-5.5")
L.prop("VECTOR_STORE_NAME", "string", "RetailKnowledge")          # BW: Weaviate class RetailKnowledge
L.prop("POLICY_DOCS_DIR", "string", "policy_docs")                 # files written before upload (relative to the exe)

# ---------------------------------------------------------------- static policy resources (exact parity)
policies = L.bw_json(LS, "ParseJSON")
URI = 'string.concat("retail://", $loop[p].documentType, "/", $loop[p].id)'

L.unlink_placeholder(LS)
items = L.static_dataset(LS, "PolicyData", {"policies": policies}, "Policy documents (BW ParseJSON literal)")
L.link(LS, "Log_API", "PolicyData")
L.project(LS, "Resources", {"resources": (
    "$activity[PolicyData].output.policies",
    'p, coerce.toString($flow.queryParams.type) == "" || $loop[p].documentType == $flow.queryParams.type',
    {"uri": ("string", "=" + URI), "name": ("string", "=$loop[p].id"), "title": ("string", "=$loop[p].title"),
     "description": ("string", '=""'), "mimeType": ("string", '="text/plain"')})},
    desc="BW choose: all resources, or only those of ?type")
L.link(LS, "PolicyData", "Resources")
L.response(LS, "ConfigureHTTPResponse", 200, "PolicyListBody", L.op(LS)["ok"],
           {"resources": "=$activity[Resources].output.resources"})
L.link(LS, "Resources", "ConfigureHTTPResponse")


def one_policy(flow, data_activity, predicate, name_expr, uri_expr, key_expr, key_label):
    L.unlink_placeholder(flow)
    its = L.static_dataset(flow, "PolicyData", {"policies": L.bw_json(flow, data_activity)},
                           f"Policy documents (BW {data_activity} literal)")
    L.require_params(flow, after="Log_API", next_step="PolicyData")
    L.select(flow, "FindPolicy", "$activity[PolicyData].output.policies", its["policies"], predicate, iterator="p",
             desc=f"Policy with the requested {key_label}")
    L.link(flow, "PolicyData", "FindPolicy")
    L.error(flow, "NotFound", 404, "policy_not_found", f'=string.concat("No policy resource with {key_label} ", {key_expr})')
    L.link(flow, "FindPolicy", "NotFound", f"{count('FindPolicy')} == 0")
    P = "$activity[FindPolicy].output.matches[0]"
    L.response(flow, "ConfigureHTTPResponse", 200, f"{flow}_Body", L.op(flow)["ok"], {
        "uri": uri_expr, "name": name_expr, "title": f"={P}.title", "description": '=""',
        "mimeType": "text/plain", "text": f"={P}.body"})
    L.link(flow, "FindPolicy", "ConfigureHTTPResponse", f"{count('FindPolicy')} > 0")


P0 = "$activity[FindPolicy].output.matches[0]"
one_policy(BYID, "ParseJSON1", "$loop[p].id == $flow.pathParams.id", "=$flow.pathParams.id",
           f'=string.concat("retail://", {P0}.documentType, "/", {P0}.id)', "$flow.pathParams.id", "id")
one_policy(RD, "ParseJSON2", f"{URI} == $flow.queryParams.uri", f"={P0}.id", "=$flow.queryParams.uri",
           "$flow.queryParams.uri", "uri")

# ---------------------------------------------------------------- shared subflows (vector store + one document)
STORE = {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}}
L.subflow("ResolveStore", "Vector store named $property[VECTOR_STORE_NAME]: reuse, recreate (reset) or create it",
          {"reset": {"type": "boolean"}}, {"storeId": {"type": "string"}})
RS = "ResolveStore"
L.openai(RS, "ListStores", "vectorstorelist", {"limit": 100}, desc="List the account's vector stores",
         outputs={"vectorStores": {"type": "array", "items": STORE}})
L.select(RS, "FindStore", "$activity[ListStores].vectorStores", STORE, '$loop[s].name == $property["VECTOR_STORE_NAME"]',
         iterator="s", desc="The store with the configured name")
L.link(RS, "ListStores", "FindStore")
found = f"{count('FindStore')} > 0"
L.sub_return(RS, "ReturnExisting", {"storeId": "=$activity[FindStore].output.matches[0].id"})
L.link(RS, "FindStore", "ReturnExisting", f"{found} && $flow.reset == false")
create_in = {"name": '=$property["VECTOR_STORE_NAME"]', "description": "Retail policy, FAQ and promotion knowledge (BW RetailKnowledge)",
             "expiresAfterDays": 0, "maxChunkSizeTokens": 800, "chunkOverlapTokens": 400}
L.openai(RS, "DeleteStore", "vectorstoredelete", {"vectorStoreId": "=$activity[FindStore].output.matches[0].id"},
         desc="resetCollection: drop the existing store")
L.link(RS, "FindStore", "DeleteStore", f"{found} && $flow.reset == true")
L.openai(RS, "RecreateStore", "vectorstorecreate", create_in, desc="resetCollection: create it again")
L.link(RS, "DeleteStore", "RecreateStore")
L.sub_return(RS, "ReturnRecreated", {"storeId": "=$activity[RecreateStore].id"})
L.link(RS, "RecreateStore", "ReturnRecreated")
L.openai(RS, "CreateStore", "vectorstorecreate", create_in, desc="First use: create the store")
L.link(RS, "FindStore", "CreateStore", f"{count('FindStore')} == 0")
L.sub_return(RS, "ReturnCreated", {"storeId": "=$activity[CreateStore].id"})
L.link(RS, "CreateStore", "ReturnCreated")

DOC_FIELDS = ("documentId", "title", "documentType", "category", "uri", "source")
L.subflow("AddDocument", "Write one document to a file and upload it into the vector store with its metadata",
          dict({"storeId": {"type": "string"}, "fileName": {"type": "string"}, "text": {"type": "string"}},
               **{f: {"type": "string"} for f in DOC_FIELDS}), {"fileId": {"type": "string"}})
AD = "AddDocument"
PATH = 'string.concat($property["POLICY_DOCS_DIR"], "/", $flow.fileName)'
L.activity(AD, "WriteDoc", "act_file_write", "Write the document text to a file (fileUpload takes a path)")
L.fda("sa", "activity", f"{AD}.WriteDoc.schemas.input.input", "--jsonFile", L.tmp("AddDocument_WriteDoc_in.json", {
    "type": "json", "value": '{"type":"object","properties":{"fileName":{"type":"string"},"overwrite":{"type":"boolean"},'
                             '"textContent":{"type":"string"}},"required":["fileName","overwrite","textContent"]}',
    "fe_metadata": '{"type":"object","properties":{"fileName":{"type":"string"},"overwrite":{"type":"boolean"},'
                   '"textContent":{"type":"string"}},"required":["fileName","overwrite","textContent"]}'}), "--force")
L._set_input(AD, "WriteDoc", "createNonExistingDir", True)
L.fda("mm", f"{AD}.WriteDoc.input.input.mapping.fileName", "=" + PATH)
L.fda("mm", f"{AD}.WriteDoc.input.input.mapping.overwrite", "=true")
L.fda("mm", f"{AD}.WriteDoc.input.input.mapping.textContent", "=$flow.text")
# fileAttributes is an untyped object input whose runtime wants [{key, value}, ...]. The designer only accepts ONE
# expression there, so build a typed object in a mapper and turn it into the key/value list with jq.
L.compute(AD, "DocAttributes", {f: ("string", f"=$flow.{f}") for f in DOC_FIELDS},
          desc="Document metadata to attach as file attributes")
L.link(AD, "WriteDoc", "DocAttributes")
L.openai(AD, "UploadDoc", "fileupload", {
    "filename": "=" + PATH, "vectorStoreID": "=$flow.storeId",
    "fileAttributes": '=json.jq($activity[DocAttributes].output, "to_entries | map({key: .key, value: (.value | tostring)}) | .[]")'},
    settings={"operation": "Upload new file", "purpose": "assistants", "maxChunkSizeTokens": 800,
              "chunkOverlapTokens": 400, "timeoutSeconds": 300},
    desc="Upload the file into the store (OpenAI chunks and embeds it); metadata as file attributes")
L.link(AD, "DocAttributes", "UploadDoc")
L.sub_return(AD, "ReturnFile", {"fileId": "=$activity[UploadDoc].id"})
L.link(AD, "UploadDoc", "ReturnFile")

# ---------------------------------------------------------------- POST /api/ingest
def normalize(d):
    """BW NormalizePolicyDocument (XPath contains() is case-sensitive)."""
    def has(*words):
        return any(w in d.get(k, "") for k in ("id", "title", "body") for w in words)
    category = ("returns" if has("return", "returns") else "warranty" if has("warranty")
                else "inventory" if has("inventory", "pickup") else "promotions" if has("promotion", "promo")
                else d.get("documentType"))
    return {"documentId": d["id"], "title": d["title"], "documentType": d["documentType"], "source": "seed-policy-json",
            "uri": f"policy://{d['id']}", "category": category, "tags": [d["documentType"]], "text": d["body"],
            "fileName": f"{d['id']}.txt"}


seed = [normalize(d) for d in L.bw_json(ING, "ParsePolicyDocs")]
L.unlink_placeholder(ING)
its = L.static_dataset(ING, "SeedDocuments", {"documents": seed}, "Seed policy documents, normalized as BW does")
L.link(ING, "Log_API", "SeedDocuments")
L.select(ING, "FilterDocuments", "$activity[SeedDocuments].output.documents", its["documents"],
         "array.contains(coerce.toArray($flow.body.documentTypes), $loop[d].documentType)", iterator="d",
         desc="Documents of the requested documentTypes (BW Iterate over documentTypes)")
L.link(ING, "SeedDocuments", "FilterDocuments")
L.call(ING, "ResolveStore", "ResolveStore", {"reset": "=$flow.body.resetCollection == true"},
       desc="Find (or with resetCollection, recreate) the vector store")
L.link(ING, "FilterDocuments", "ResolveStore")
L.call(ING, "AddDocuments", "AddDocument", dict(
    {"storeId": "=$activity[ResolveStore].storeId", "fileName": "=$iteration[value].fileName",
     "text": "=$iteration[value].text"}, **{f: f"=$iteration[value].{f}" for f in DOC_FIELDS}),
    iterate="=$activity[FilterDocuments].output.matches", desc="Upload each document (once per document)")
L.link(ING, "ResolveStore", "AddDocuments")
CH = {"chunkId": ("string", '=string.concat($loop[c].documentId, "-", utils.uuid())'),
      "title": ("string", "=$loop[c].title"), "documentType": ("string", "=$loop[c].documentType"),
      "tokenCount": ("integer", "=0")}
L.project(ING, "IngestionSummary", {
    "sampleChunks": ("$activity[FilterDocuments].output.matches", "c", dict(CH, documentId=("string", "=$loop[c].documentId"))),
    "statusChunks": ("$activity[FilterDocuments].output.matches", "c", CH)},
    desc="BW BuildIngestionSummary: one chunk entry per document")
L.link(ING, "AddDocuments", "IngestionSummary")
n_docs = f"=array.count($activity[FilterDocuments].output.matches)"
L.response(ING, "ConfigureHTTPResponse", 200, "IngestBody", L.op(ING)["ok"], {
    "ingestion.sourceCount": n_docs, "ingestion.chunkCount": n_docs,
    "ingestion.embedding.provider": "openai-vector-store", "ingestion.embedding.model": "text-embedding-3-large",
    "ingestion.storage.provider": "openai", "ingestion.storage.collection": '=$property["VECTOR_STORE_NAME"]',
    "ingestion.sampleChunks": "=$activity[IngestionSummary].output.sampleChunks",
    "status.dataset.products": 10, "status.dataset.inventory": 3, "status.dataset.customers": 4,
    "status.dataset.orders": 5, "status.dataset.policies": 3,
    "status.ingestion.sourceCount": n_docs, "status.ingestion.chunkCount": n_docs,
    "status.ingestion.embedding": {}, "status.ingestion.storage": {},
    "status.ingestion.sampleChunks": "=$activity[IngestionSummary].output.statusChunks"})
L.link(ING, "IngestionSummary", "ConfigureHTTPResponse")

# ---------------------------------------------------------------- POST /api/upload
b = "$flow.body"
fn = f"{b}.fileName"
L.unlink_placeholder(UPL)
L.compute(UPL, "UploadInfo", {
    "documentId": ("string", '=string.concat("upload-", datetime.currentDate())'),
    "text": ("string", f"=string.base64ToString({b}.contentBase64)"),
    "category": ("string", f'=string.contains({fn}, "return") ? "returns" : (string.contains({fn}, "warranty") ? "warranty" : '
                           f'((string.contains({fn}, "inventory") || string.contains({fn}, "pickup")) ? "inventory" : '
                           f'((string.contains({fn}, "promotion") || string.contains({fn}, "promo")) ? "promotions" : "uploaded")))')},
    desc="BW DecodeBase64Content + NormalizePolicyDocument2")
L.require_params(UPL, after="Log_API", next_step="UploadInfo", body_fields=("fileName", "contentBase64"))
L.call(UPL, "ResolveStore", "ResolveStore", {"reset": "=false"}, desc="Find (or create) the vector store")
L.link(UPL, "UploadInfo", "ResolveStore")
L.call(UPL, "AddUpload", "AddDocument", {
    "storeId": "=$activity[ResolveStore].storeId", "fileName": f"={fn}", "text": "=$activity[UploadInfo].output.text",
    "documentId": "=$activity[UploadInfo].output.documentId", "title": f"={fn}", "documentType": "document",
    "category": "=$activity[UploadInfo].output.category", "uri": f'=string.concat("upload://", {fn})', "source": "upload"},
    desc="Upload the document into the store")
L.link(UPL, "ResolveStore", "AddUpload")
L.response(UPL, "ConfigureHTTPResponse", 200, "UploadBody", L.op(UPL)["ok"], {
    "upload.uploadId": "=$activity[UploadInfo].output.documentId", "upload.fileName": f"={fn}", "upload.status": "completed",
    "upload.documentCount": 1, "upload.productCount": 0, "upload.chunkCount": 1,
    "upload.uploadedAt": "=datetime.currentDatetime()"})
L.link(UPL, "AddUpload", "ConfigureHTTPResponse")

# ---------------------------------------------------------------- POST /api/policy/query
system_prompt = re.search(r'<systemPrompt><value-of select=""(.*?)""/>', L.bw_activity(QRY, "Query")["inputXslt"][0]).group(1)
ATTR = lambda it, k: f"$loop[{it}].attributes.{k}.OfString"
ROW = {"type": "object", "properties": {
    "attributes": {"type": "object", "properties": {f: {"type": "object", "properties": {"OfString": {"type": "string"}}}
                                                    for f in DOC_FIELDS}},
    "content": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "type": {"type": "string"}}}},
    "file_id": {"type": "string"}, "filename": {"type": "string"}, "score": {"type": "number"}}}
L.unlink_placeholder(QRY)
L.call(QRY, "ResolveStore", "ResolveStore", {"reset": "=false"}, desc="Find (or create) the vector store")
L.require_params(QRY, after="Log_API", next_step="ResolveStore", body_fields=("question",))
L.openai(QRY, "Search", "vectorsearch", {"vectorStoreID": "=$activity[ResolveStore].storeId",
                                         "searchString": f"={b}.question", "maxNumberOfResults": 5, "rewriteQuery": False},
         desc="Semantic search (BW RAG query retrieval, maxResult 5)", outputs={"searchResultRows": {"type": "array", "items": ROW}})
L.link(QRY, "ResolveStore", "Search")
# vectorSearch returns typed SDK structs ([]*openai.VectorStoreSearchResponse); field access and json.jq need plain JSON.
# coerce.toString marshals them (attribute unions become {"OfString": ..}), coerce.toArray parses that back.
L.compute(QRY, "SearchRows", {"rows": ({"type": "array", "items": ROW},
                                       "=coerce.toArray(coerce.toString($activity[Search].searchResultRows))")},
          desc="Search results as plain JSON")
L.link(QRY, "Search", "SearchRows")
L.project(QRY, "Retrieval", {
    "retrieval": ("$activity[SearchRows].output.rows", "r", {
        "chunkId": ("string", '=string.concat("rag-", $loop[r].file_id)'), "documentId": ("string", "=" + ATTR("r", "documentId")),
        "title": ("string", "=" + ATTR("r", "title")), "documentType": ("string", "=" + ATTR("r", "documentType")),
        "category": ("string", "=" + ATTR("r", "category")), "uri": ("string", "=" + ATTR("r", "uri")),
        "score": ("number", "=$loop[r].score"),
        "text": ("string", "=$loop[r].content[0].text")}),
    "citations": ("$activity[SearchRows].output.rows", "r", {
        "id": ("string", '=string.concat("rag-", $loop[r].file_id)'), "title": ("string", "=" + ATTR("r", "title")),
        "documentType": ("string", "=" + ATTR("r", "documentType")), "uri": ("string", "=" + ATTR("r", "uri"))})},
    desc="BW BuildRetrieval + BuildCitations (metadata read from the file attributes)")
L.link(QRY, "SearchRows", "Retrieval")
L.llm(QRY, "Answer", system_prompt,
      f'=string.concat("Question: ", {b}.question, " | Retrieved retail knowledge (JSON): ", '
      f'utility.renderJSON($activity[Retrieval].output.retrieval, false))',
      desc="Answer from the retrieved knowledge (BW RAG query answer)",
      key_prop="OPENAI_API_KEY")   # same key as the openAI extension activities (one property, set at run time)
L.link(QRY, "Retrieval", "Answer")
L.response(QRY, "ConfigureHTTPResponse", 200, "PolicyQueryBody", L.op(QRY)["ok"], {
    "question": f"={b}.question", "answer": "=$activity[Answer].response",
    "retrieval": "=$activity[Retrieval].output.retrieval", "citations": "=$activity[Retrieval].output.citations",
    "raw.selectedEmbeddings": '=json.jq($activity[SearchRows].output.rows, ".[] | .content[0].text")',
    "metadata.provider": "openai", "metadata.collection": '=$property["VECTOR_STORE_NAME"]',
    "metadata.embedding.provider": "openai-vector-store", "metadata.embedding.model": "text-embedding-3-large",
    "metadata.topK": 5, "metadata.minScore": 0, "metadata.retrievalCount": 0})
L.link(QRY, "Answer", "ConfigureHTTPResponse")

sys.exit(L.finish())
