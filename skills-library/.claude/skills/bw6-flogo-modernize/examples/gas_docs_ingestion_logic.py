#!/usr/bin/env python3
"""Business logic of a document-ingestion API (BW AI-plugin RAG ingest) rebuilt in Flogo (worked example: multipart
file upload, per-file binary write, OpenAI vector store via the repo-local openAI extension, an MCP tool over a
multipart operation).

BW6 source (decoded by analyze_bw6.py):
  POST /upload  multipart "files" (binary[])
       Iterate files -> WriteFile (concat(<dir>, filename) - no path separator)
       -> Chunk (the folder of the last written file) -> Ingest (local vector-store file, text-embedding-3-large)
       -> reply {filePath: "Files uploaded to AS DataGrid successfully from the location : <folder>"}

Flogo design:
  - multipart handler (Logic.multipart): "files" (filecontent, required) + optional "fileNames" (JSON list of the
    original names, in upload order). The REST trigger delivers file BYTES only (no names); without fileNames the
    files are called upload-1.txt, upload-2.txt ...
  - ResolveStore subflow: the OpenAI vector store named $property[VECTOR_STORE_NAME], created on first use.
  - AddFile subflow (iterator, once per file): write the bytes to <DOCS_DIR>/<name> (File write, Binary; the bytes
    render as a quoted base64 string) -> upload into the store with fileName/source as file attributes.
    Only the uploaded files are ingested (BW re-chunks the whole folder).
  - reply {filePath: "Files uploaded to vector store successfully from the location : <DOCS_DIR>"} (wording chosen
    by the user: the storage is a vector store, not AS DataGrid).
  - MCP tool post-upload (BW: {files: binary[]}): {files: [base64 content], fileNames?: [names]} -> same flow.

Usage: python gas_docs_ingestion_logic.py <work>/plan.json
       (export FLOGO_DESIGN_CONFIG_FILE=<work>/fda-config.json from extend_fda_catalog.py first)
API key: OPENAI_API_KEY is a plain-string PLACEHOLDER; supply it at run time: FLOGO_APP_PROPS_ENV=auto OPENAI_API_KEY=...
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from flogo_logic_lib import Logic, jschema  # noqa: E402

L = Logic(sys.argv[1] if len(sys.argv) > 1 else None)   # <work>/plan.json from scaffold_flogo_app.py
F = L.flow("post_upload")
count = lambda act: f"array.count($activity[{act}].output.matches)"

# ---------------------------------------------------------------- app properties
L.prop("OPENAI_API_KEY", "string", "YOUR_OPENAI_API_KEY")      # placeholder: real key via env at run time
L.prop("OPENAI_API_ENDPOINT_URL", "string", "https://api.openai.com/v1")
L.prop("VECTOR_STORE_NAME", "string", "IndustrialGasDocs")     # shared with the query app
L.prop("DOCS_DIR", "string", "gas_docs")                        # uploaded files are written here (relative to the exe)

# ---------------------------------------------------------------- multipart input
# "files" is checked in the flow (JSON 400) instead of by the trigger, which answers a missing part in plain text
L.multipart(F, [("files", "filecontent", False), ("fileNames", "string", False)])

# ---------------------------------------------------------------- ResolveStore: find-or-create the vector store
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

# ---------------------------------------------------------------- AddFile: write one upload, put it into the store
AF = "AddFile"
L.subflow(AF, "Write one uploaded file and upload it into the vector store",
          {"content": {"type": "any"}, "index": {"type": "integer"}, "names": {"type": "string"},
           "storeId": {"type": "string"}}, {"fileName": {"type": "string"}, "fileId": {"type": "string"}})
L.compute(AF, "Name", {"fileName": ("string",
    '=coerce.toString($flow.names) != "" && array.count(coerce.toArray($flow.names)) > $flow.index ? '
    'coerce.toString(array.get(coerce.toArray($flow.names), $flow.index)) : '
    'string.concat("upload-", coerce.toString($flow.index + 1), ".txt")')},
    desc="Original file name from fileNames (the trigger drops it), else upload-<n>.txt")
PATH = 'string.concat($property["DOCS_DIR"], "/", $activity[Name].output.fileName)'
W_SCHEMA = ('{"type":"object","properties":{"fileName":{"type":"string"},"overwrite":{"type":"boolean"},'
            '"binaryContent":{"type":"string"}},"required":["fileName","overwrite","binaryContent"]}')
L.activity(AF, "WriteFile", "act_file_write", "Write the uploaded bytes (fileUpload reads a path)")
L._set_input(AF, "WriteFile", "writeAs", "Binary")
L.fda("sa", "activity", f"{AF}.WriteFile.schemas.input.input", "--jsonFile",
      L.tmp("AddFile_WriteFile_in.json", {"type": "json", "value": W_SCHEMA, "fe_metadata": W_SCHEMA}), "--force")
L._set_input(AF, "WriteFile", "createNonExistingDir", True)
L.fda("mm", f"{AF}.WriteFile.input.input.mapping.fileName", "=" + PATH)
L.fda("mm", f"{AF}.WriteFile.input.input.mapping.overwrite", "=true")
# file bytes render as a quoted base64 string; Binary write base64-decodes binaryContent once (verified byte-for-byte)
L.fda("mm", f"{AF}.WriteFile.input.input.mapping.binaryContent",
      '=string.replaceAll(utility.renderJSON($flow.content, false), "\\"", "")')
L.link(AF, "Name", "WriteFile")
L.compute(AF, "FileAttributes", {"fileName": ("string", "=$activity[Name].output.fileName"),
                                 "source": ("string", "upload")}, desc="Metadata stored with the file (search returns it)")
L.link(AF, "WriteFile", "FileAttributes")
L.openai(AF, "UploadFile", "fileupload", {
    "filename": "=" + PATH, "vectorStoreID": "=$flow.storeId",
    "fileAttributes": '=json.jq($activity[FileAttributes].output, "to_entries | map({key: .key, value: (.value | tostring)}) | .[]")'},
    settings={"operation": "Upload new file", "purpose": "assistants", "maxChunkSizeTokens": 800,
              "chunkOverlapTokens": 400, "timeoutSeconds": 300},
    desc="Upload into the store (OpenAI chunks and embeds it)")
L.link(AF, "FileAttributes", "UploadFile")
L.sub_return(AF, "ReturnFile", {"fileName": "=$activity[Name].output.fileName", "fileId": "=$activity[UploadFile].id"})
L.link(AF, "UploadFile", "ReturnFile")

# ---------------------------------------------------------------- POST /upload
L.unlink_placeholder(F)
L.log(F, '=string.concat("upload files=", coerce.toString(array.count($flow.multipartFormData.files)))')
L.call(F, "GetStore", RS, {}, desc="Resolve the vector store")
NFILES = "array.count($flow.multipartFormData.files)"
L.error(F, "BadRequest", 400, "invalid_request", "files is required (multipart form field 'files')")
L.link(F, "Log_API", "BadRequest", f"{NFILES} == 0")
L.link(F, "Log_API", "GetStore", f"{NFILES} > 0")
L.call(F, "AddFiles", AF, {"content": "=$iteration[value]", "index": "=$iteration[index]",
                           "names": "=$flow.multipartFormData.fileNames", "storeId": "=$activity[GetStore].storeId"},
       iterate="=$flow.multipartFormData.files", desc="Write + upload each file")
L.link(F, "GetStore", "AddFiles")
L.response(F, "ConfigureHTTPResponse", 200, "FileDataBody", L.op(F)["ok"], {
    "filePath": '=string.concat("Files uploaded to vector store successfully from the location : ", $property["DOCS_DIR"])'})
L.link(F, "AddFiles", "ConfigureHTTPResponse")

# ---------------------------------------------------------------- MCP tool post-upload -> the same flow
M = L.op(F)["mcpFlow"]                                       # mcp_<tool> flow the scaffold created
ARGS = {"$schema": "http://json-schema.org/draft-04/schema#", "type": "object", "required": ["files"], "properties": {
    "files": {"type": "array", "items": {"type": "string"}, "description": "file contents, base64-encoded"},
    "fileNames": {"type": "array", "items": {"type": "string"}, "description": "original file names, same order"}}}
L.mcp_tool_args(M, ARGS)   # handler + tool-flow input, so the designer resolves $flow.arguments.<field>
L.fda("rl", M, "StartActivity", "CallOperation")
L.compute(M, "Form", {"files": ({"type": "array", "items": {"type": "string"}}, "=$flow.arguments.files"),
                      "fileNames": ("string", '=coerce.toString($flow.arguments.fileNames) != "" ? '
                                              'utility.renderJSON($flow.arguments.fileNames, false) : ""')},
          desc="Tool arguments -> the operation's multipart form")
L.link(M, "StartActivity", "Form")
L.fda("mm", f"{M}.CallOperation.input.multipartFormData", "=$activity[Form].output")
L.link(M, "Form", "CallOperation")

sys.exit(L.finish())
