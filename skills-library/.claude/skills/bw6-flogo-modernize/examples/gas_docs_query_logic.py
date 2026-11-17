#!/usr/bin/env python3
"""Business logic of a RAG question-answering API with optional images (BW AI-plugin RAG query) rebuilt in Flogo
(worked example: multipart question + images, OpenAI vector search, LLM Client for text, Invoke REST to the OpenAI
chat API for questions with images, request built with json.jq, an MCP tool over a multipart operation).

BW6 source (decoded by analyze_bw6.py):
  POST /ragimgquery  multipart "question" (required) + "imageInput" (binary[])
       [images] Iterate -> WriteFile imageData/<name> -> ListFiles
       -> Query (local vector store retrieval + gpt-5.5, temperature 1, maxTokens 5000, grounded system prompt with
          inline [n] citations and a Sources section) -> reply {answer}

Flogo design:
  - multipart (Logic.multipart): question (checked in the flow -> JSON 400), imageInput (files).
  - ResolveStore (find-or-create the store named $property[VECTOR_STORE_NAME]) -> vectorSearch (5 results) -> the
    retrieved chunks as JSON {fileName, text} for the prompt (file names come from the file attributes the
    ingestion API stored).
  - no images: Agentic AI LLM Client with BW's system prompt (verified pattern).
  - images: the LLM Client takes text only, so a Mapper + json.jq builds an OpenAI chat-completions request
    (text + each image as a data: URL; type detected from the first bytes: PNG, JPEG, GIF, WEBP) and Invoke REST
    posts it. Unsupported image types -> JSON 400.
  - reply {answer}; MCP tool post-ragimgquery {question, imageInput: [base64]} -> same flow.

Usage: python gas_docs_query_logic.py <work>/plan.json
       (export FLOGO_DESIGN_CONFIG_FILE=<work>/fda-config.json from extend_fda_catalog.py first)
API key: OPENAI_API_KEY is a plain-string PLACEHOLDER; supply it at run time: FLOGO_APP_PROPS_ENV=auto OPENAI_API_KEY=...
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic, jschema  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
F = L.flow("post_ragimgquery")
count = lambda act: f"array.count($activity[{act}].output.matches)"
Q = "$flow.multipartFormData.question"

# ---------------------------------------------------------------- app properties
L.prop("OPENAI_API_KEY", "string", "YOUR_OPENAI_API_KEY")      # placeholder: real key via env at run time
L.prop("OPENAI_API_ENDPOINT_URL", "string", "https://api.openai.com/v1")
L.prop("OPENAI_CHAT_COMPLETIONS_URL", "string", "https://api.openai.com/v1/chat/completions")  # Invoke REST Uri: one whole property
L.prop("LLM_PROVIDER", "string", "OpenAI")
L.prop("LLM_MODEL", "string", "gpt-5.5")                        # BW ragResource openAIModelType
L.prop("VECTOR_STORE_NAME", "string", "IndustrialGasDocs")     # filled by the ingestion API

# ---------------------------------------------------------------- multipart input
L.multipart(F, [("question", "string", False), ("imageInput", "filecontent", False)])

# ---------------------------------------------------------------- ResolveStore (same as the ingestion app)
STORE = {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}}
RS = "ResolveStore"
L.subflow(RS, "The vector store named $property[VECTOR_STORE_NAME] (created on first use)", {}, {"storeId": {"type": "string"}})
L.openai(RS, "ListStores", "vectorstorelist", {"limit": 100}, desc="List the account's vector stores",
         outputs={"vectorStores": {"type": "array", "items": STORE}})
L.select(RS, "FindStore", "$activity[ListStores].vectorStores", STORE, '$loop[s].name == $property["VECTOR_STORE_NAME"]',
         iterator="s", desc="The store with the configured name")
L.link(RS, "ListStores", "FindStore")
L.sub_return(RS, "ReturnExisting", {"storeId": "=$activity[FindStore].output.matches[0].id"})
L.link(RS, "FindStore", "ReturnExisting", f"{count('FindStore')} > 0")
L.openai(RS, "CreateStore", "vectorstorecreate", {
    "name": '=$property["VECTOR_STORE_NAME"]', "description": "Industrial gas safety data sheets, manuals and certificates",
    "expiresAfterDays": 0, "maxChunkSizeTokens": 800, "chunkOverlapTokens": 400}, desc="First use: create the store")
L.link(RS, "FindStore", "CreateStore", f"{count('FindStore')} == 0")
L.sub_return(RS, "ReturnCreated", {"storeId": "=$activity[CreateStore].id"})
L.link(RS, "CreateStore", "ReturnCreated")

# ---------------------------------------------------------------- retrieve
# BW's own grounded system prompt, read from the decoded Query mapping
system_prompt = next(lit for a in L.op(F)["bwActivities"] for x in a["inputXslt"]
                     for lit in re.findall(r"systemPrompt=\{'(.*?)'\}", x, re.S))
ROW = {"type": "object", "properties": {
    "attributes": {"type": "object", "properties": {"fileName": {"type": "object", "properties": {"OfString": {"type": "string"}}}}},
    "content": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "type": {"type": "string"}}}},
    "file_id": {"type": "string"}, "filename": {"type": "string"}, "score": {"type": "number"}}}

L.unlink_placeholder(F)
L.log(F, '=string.concat("ragimgquery question=", coerce.toString($flow.multipartFormData.question))')
L.error(F, "BadRequest", 400, "invalid_request", "question is required (multipart form field 'question')")
L.link(F, "Log_API", "BadRequest", f'coerce.toString({Q}) == ""')
L.call(F, "GetStore", RS, {}, desc="Resolve the vector store")
L.link(F, "Log_API", "GetStore", f'coerce.toString({Q}) != ""')
L.openai(F, "Search", "vectorsearch", {"vectorStoreID": "=$activity[GetStore].storeId", "searchString": "=" + Q,
                                       "maxNumberOfResults": 5, "rewriteQuery": False},
         desc="Semantic search in the document store", outputs={"searchResultRows": {"type": "array", "items": ROW}})
L.link(F, "GetStore", "Search")
# vectorSearch returns typed SDK structs; coerce.toString marshals them (attribute unions -> {"OfString": ..}),
# coerce.toArray parses that back into plain JSON
L.compute(F, "SearchRows", {"rows": ({"type": "array", "items": ROW},
                                     "=coerce.toArray(coerce.toString($activity[Search].searchResultRows))")},
          desc="Search results as plain JSON")
L.link(F, "Search", "SearchRows")
L.project(F, "Retrieval", {"documents": ("$activity[SearchRows].output.rows", "r", {
    "fileName": ("string", "=$loop[r].attributes.fileName.OfString"), "text": ("string", "=$loop[r].content[0].text")})},
    desc="Retrieved chunks with their source file names")
L.link(F, "SearchRows", "Retrieval")

USER_TEXT = ('=string.concat("Question: ", ' + Q + ', " | Retrieved context documents (JSON, cite them in this order): ", '
             'utility.renderJSON($activity[Retrieval].output.documents, false))')
# jq programs go in single-quoted Flogo strings (they contain double quotes; fda's validator rejects backticks)
# both REST bytes and MCP base64 strings render as a JSON array of base64 strings
IMAGES = "coerce.toArray(utility.renderJSON($flow.multipartFormData.imageInput, false))"
sq = lambda prog: "'" + prog + "'"     # Flogo single-quoted string literal (the jq program has no single quotes)
JQ_BAD = sq('[(.images // [])[] | select((startswith("iVBOR") or startswith("/9j/") or startswith("R0lGOD") or '
            'startswith("UklGR")) | not)] | length')
L.compute(F, "ChatInput", {
    "model": ("string", '=$property["LLM_MODEL"]'), "system": ("string", system_prompt), "text": ("string", USER_TEXT),
    "images": ({"type": "array", "items": {"type": "string"}}, "=" + IMAGES)}, desc="Question, context and images")
L.link(F, "Retrieval", "ChatInput")
L.compute(F, "ImageCheck", {"imageCount": ("integer", "=array.count($activity[ChatInput].output.images)"),
                            "unsupported": ("integer", f"=coerce.toInt(array.get(json.jq($activity[ChatInput].output, {JQ_BAD}), 0))")},
          desc="How many images, how many of an unsupported type")
L.link(F, "ChatInput", "ImageCheck")
N, BAD = "$activity[ImageCheck].output.imageCount", "$activity[ImageCheck].output.unsupported"

# ---- text only: LLM Client (verified pattern)
L.llm(F, "Answer", system_prompt, "=$activity[ChatInput].output.text", desc="Grounded answer (BW RAG query)",
      key_prop="OPENAI_API_KEY", temperature=1)
L.link(F, "ImageCheck", "Answer", f"{N} == 0")
L.response(F, "ConfigureHTTPResponse", 200, "AnswerBody", L.op(F)["ok"], {"answer": "=$activity[Answer].response"})
L.link(F, "Answer", "ConfigureHTTPResponse")

# ---- unsupported image
L.error(F, "BadImage", 400, "unsupported_image", "imageInput accepts PNG, JPEG, GIF or WEBP images")
L.link(F, "ImageCheck", "BadImage", f"{N} > 0 && {BAD} > 0")

# ---- with images: OpenAI chat completions through Invoke REST
JQ_REQ = sq('{model: .model, max_completion_tokens: 5000, messages: [{role: "system", content: .system}, '
            '{role: "user", content: ([{type: "text", text: .text}] + [(.images // [])[] | '
            '(if startswith("iVBOR") then "image/png" elif startswith("/9j/") then "image/jpeg" '
            'elif startswith("R0lGOD") then "image/gif" else "image/webp" end) as $m | '
            '{type: "image_url", image_url: {url: ("data:" + $m + ";base64," + .)}}])}]}')
# json.jq returns the LIST of the program's results: take the first (the request object)
L.compute(F, "ChatRequest", {"request": ({"type": "object"}, f"=array.get(json.jq($activity[ChatInput].output, {JQ_REQ}), 0)")},
          desc="OpenAI chat request: text + images as data URLs")
L.link(F, "ImageCheck", "ChatRequest", f"{N} > 0 && {BAD} == 0")
A = "AskWithImages"
BODY = {"type": "object", "properties": {"model": {"type": "string"}, "max_completion_tokens": {"type": "integer"},
                                         "messages": {"type": "array", "items": {"type": "object"}}}}
RESP = {"type": "object", "properties": {"choices": {"type": "array", "items": {"type": "object", "properties": {
    "message": {"type": "object", "properties": {"content": {"type": "string"}}}}}}}}
L.rest_invoke(F, A, "POST", "OPENAI_CHAT_COMPLETIONS_URL", body_schema=BODY, body_expr="=$activity[ChatRequest].output.request",
              response_schema=RESP, headers={"Authorization": '=string.concat("Bearer ", $property["OPENAI_API_KEY"])'},
              timeout_ms=180000, desc="OpenAI chat completions with the images (the LLM Client is text-only)")
L.link(F, "ChatRequest", A)
L.response(F, "ImageAnswer", 200, "AnswerBody", L.op(F)["ok"],
           {"answer": f"=$activity[{A}].responseBody.choices[0].message.content"})
L.link(F, A, "ImageAnswer")

# ---------------------------------------------------------------- MCP tool post-ragimgquery -> the same flow
M = L.op(F)["mcpFlow"]
ARGS = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object", "required": ["question"], "properties": {
    "question": {"type": "string"},
    "imageInput": {"type": "array", "items": {"type": "string"}, "description": "images, base64-encoded (PNG, JPEG, GIF, WEBP)"}}}
L.mcp_tool_args(M, ARGS)   # handler + tool-flow input, so the designer resolves $flow.arguments.<field>
L.fda("rl", M, "StartActivity", "CallOperation")
L.compute(M, "Form", {"question": ("string", "=$flow.arguments.question"),
                      "imageInput": ({"type": "array", "items": {"type": "string"}}, "=$flow.arguments.imageInput")},
          desc="Tool arguments -> the operation's multipart form")
L.link(M, "StartActivity", "Form")
L.fda("mm", f"{M}.CallOperation.input.multipartFormData", "=$activity[Form].output")
L.link(M, "Form", "CallOperation")

sys.exit(L.finish())
