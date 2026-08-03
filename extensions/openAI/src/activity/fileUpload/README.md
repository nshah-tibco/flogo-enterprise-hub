# Upload File Activity

## Overview

The Upload File activity enables you to upload files to OpenAI's file storage system for use with various OpenAI services including assistants, fine-tuning, batch processing, and vector stores. This activity provides comprehensive file management capabilities with support for custom metadata, chunking strategies, and automatic vector store integration.

This activity uses the OpenAI Files API endpoint: `https://api.openai.com/v1/files`

## Prerequisites

- Valid OpenAI API key with file upload permissions
- Local file system access to files for upload
- Flogo Enterprise application

## Settings

The Upload File activity requires the following connection and configuration settings:

| Setting | Type | Required | Default | Description |
|---------|------|----------|---------|-------------|
| **API Endpoint URL** | String | Yes | - | The base URL for the OpenAI API. Typically `https://api.openai.com/v1`. Supports app properties. |
| **OpenAI API Key** | String | Yes | - | Your OpenAI API authentication key required for file operations. Supports app properties for secure storage. |
| **Purpose** | String | Yes | "assistants" | The intended purpose of the uploaded file. Determines how OpenAI processes and uses the file. |
| **Maximum Chunk Size Tokens** | Integer | No | 800 | Maximum number of tokens per chunk when adding to vector store. Range: 100-4096. |
| **Chunk Overlap Tokens** | Integer | No | 400 | Number of tokens that overlap between adjacent chunks for better context preservation. |
| **Timeout in Seconds** | Integer | Yes | 300 | Upload timeout duration in seconds. Increase for large files or slow connections. |

### Purpose Options

The **Purpose** setting accepts the following values:

| Purpose | Description |
|---------|-------------|
| `assistants` | Files for use with OpenAI Assistants API (default) |
| `batch` | Files for batch processing operations |
| `fine-tune` | Training data files for model fine-tuning |
| `vision` | Images for vision model processing |
| `user_data` | User-provided data files |
| `evals` | Evaluation datasets |

### Configuration Example
```
API Endpoint URL: https://api.openai.com/v1
OpenAI API Key: sk-your-openai-api-key-here
Purpose: assistants
Maximum Chunk Size Tokens: 800
Chunk Overlap Tokens: 400
Timeout in Seconds: 600
```

## Input

The Upload File activity accepts the following input parameters:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| **filename** | String | Yes | Full path to the local file to upload. Must be accessible from the Flogo runtime environment. |
| **vectorStoreID** | String | Yes | Identifier of the OpenAI vector store the uploaded file is added to (with chunking). |
| **fileAttributes** | Object | No | Custom metadata key-value pairs to associate with the file when adding to a vector store. |

### Input Guidelines

- **filename**: Must be an absolute or relative path to an existing file
- **vectorStoreID**: Must reference an existing OpenAI vector store; the activity will fail if it is empty
- **fileAttributes**: Structure should contain key-value pairs as objects with "key" and "value" properties

### File Attributes Example
```json
{
  "fileAttributes": [
    {
      "key": "department",
      "value": "engineering"
    },
    {
      "key": "document_type",
      "value": "specification"
    },
    {
      "key": "version",
      "value": "2.1"
    }
  ]
}
```

## Output

The activity returns detailed information about the uploaded file.

| Output | Type | Description |
|--------|------|-------------|
| **id** | String | Unique OpenAI file identifier for the uploaded file |
| **object** | String | Object type, typically "file" |
| **bytes** | String | File size in bytes |
| **createdAt** | String | Upload timestamp in Unix epoch format |
| **filename** | String | Original filename as stored in OpenAI |
| **purpose** | String | Confirmed purpose classification for the file |

### Output Example
```json
{
  "id": "file-abc123def456",
  "object": "file",
  "bytes": "245760",
  "createdAt": "1640995200",
  "filename": "user_manual.pdf",
  "purpose": "assistants"
}
```

## Supported File Types

The activity automatically detects MIME types and supports various file formats including:

- **Documents**: PDF, Word, Text files
- **Images**: PNG, JPEG, GIF, WebP
- **Data**: JSON, CSV, JSONL
- **Code**: Various programming language files

File type support may vary depending on the specified **Purpose**.

## Vector Store Integration

The activity always adds the uploaded file to the vector store identified by the required **vectorStoreID** input. Specifically, it:

1. Uploads the file to OpenAI file storage
2. Processes the file content using the configured chunking strategy
3. Adds the processed chunks to the specified vector store
4. Associates custom metadata with each chunk

### Chunking Strategy

The activity uses a static chunking strategy with the following parameters:

- **Max Chunk Size**: Configurable token limit per chunk (100-4096)
- **Chunk Overlap**: Token overlap between chunks for context preservation
- **Custom Metadata**: Applied to all chunks created from the file

## Usage Examples

### Basic File Upload

Upload a document for assistant use:

```
Settings:
- Purpose: "assistants"
- Vector Store ID: (empty)
- Timeout: 300

Inputs:
- filename: "/path/to/user_manual.pdf"
- fileAttributes: (empty)
```

### Vector Store Integration

Upload with automatic vector store processing:

```
Settings:
- Purpose: "assistants"
- Vector Store ID: "vs-abc123def456"
- Max Chunk Size Tokens: 1000
- Chunk Overlap Tokens: 200
- Timeout: 600

Inputs:
- filename: "/documents/knowledge_base.pdf"
- fileAttributes: [
    {"key": "category", "value": "documentation"},
    {"key": "priority", "value": "high"}
  ]
```

### Fine-tuning Data Upload

Upload training data for model fine-tuning:

```
Settings:
- Purpose: "fine-tune"
- Vector Store ID: (empty)
- Timeout: 900

Inputs:
- filename: "/training_data/examples.jsonl"
- fileAttributes: (empty)
```

### Batch Processing File

Upload file for batch operations:

```
Settings:
- Purpose: "batch"
- Vector Store ID: (empty)
- Timeout: 1200

Inputs:
- filename: "/batch_jobs/requests.jsonl"
- fileAttributes: (empty)
```

## Error Handling

The activity provides comprehensive error handling for common scenarios:

### Upload Errors
- **File Not Found**: Invalid or inaccessible file path
- **Permission Denied**: Insufficient file system permissions
- **Timeout**: Upload exceeds configured timeout duration
- **API Rate Limits**: Automatic retry with exponential backoff

### Vector Store Errors
- **Invalid Vector Store ID**: Non-existent or inaccessible vector store
- **Chunking Failures**: Issues with content processing or tokenization
- **Metadata Errors**: Invalid custom attribute formatting

### Validation Errors
- **Missing API Key**: Authentication configuration issues
- **Invalid Purpose**: Unsupported file purpose specification
- **File Size Limits**: Files exceeding OpenAI's size restrictions

## Best Practices

### Security
1. **API Key Management**: Always use app properties for secure API key storage
2. **File Path Validation**: Ensure file paths are validated and sanitized
3. **Access Control**: Limit file system access to necessary directories

### Performance
1. **Timeout Configuration**: Set appropriate timeouts based on file sizes and network conditions
2. **Chunking Optimization**: Adjust chunk sizes based on content type and use case
3. **Batch Operations**: Group multiple file uploads when possible

### Vector Store Integration
1. **Metadata Design**: Use consistent and meaningful metadata keys across files
2. **Chunk Overlap**: Configure overlap based on content structure and search requirements
3. **Purpose Alignment**: Ensure file purpose matches intended vector store usage

### File Management
1. **File Organization**: Maintain organized file structures for easier management
2. **Version Control**: Include version information in metadata for document tracking
3. **Cleanup**: Regularly review and manage uploaded files to control storage costs

## Related OpenAI API Documentation

- [Files API](https://platform.openai.com/docs/api-reference/files)
- [Vector Stores API](https://platform.openai.com/docs/api-reference/vector-stores)
- [Assistants File Search](https://platform.openai.com/docs/assistants/tools/file-search)
- [Fine-tuning](https://platform.openai.com/docs/guides/fine-tuning)
- [Batch API](https://platform.openai.com/docs/guides/batch)

## Version Information

- **Activity Version**: 1.0.1
- **Supported OpenAI API Version**: v1
- **Flogo Category**: openAI
- **Retry Support**: Enabled with automatic exponential backoff