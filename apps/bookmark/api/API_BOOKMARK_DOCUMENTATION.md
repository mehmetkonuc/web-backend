# Bookmark API Documentation

This document describes the API endpoints available for the Bookmark module.

## Overview

The Bookmark API allows users to save and manage bookmarks for different content types throughout the platform, such as posts, comments, etc. Users can bookmark content, remove bookmarks, and view their bookmarked items.

## Authentication

All endpoints require authentication unless explicitly stated otherwise.

## Base URL

```
/api/v1/bookmark/
```

## Endpoints

### List Bookmarks

Retrieves a list of bookmarks, with optional filtering.

- **URL**: `/api/v1/bookmark/`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `content_type_id` (optional): Filter by content type ID
  - `object_id` (optional): Filter by object ID
  - `user_id` (optional): Filter by user ID
- **Success Response**: 
  ```json
  [
    {
      "id": 1,
      "user": {
        "id": 1,
        "username": "username",
        "avatar_url": "https://example.com/media/avatars/user.jpg",
        "full_name": "User Name",
        "is_verified": true
      },
      "created_at": "2023-05-18T12:00:00Z"
    }
  ]
  ```

### Create Bookmark

Creates a new bookmark for a specific content object.

- **URL**: `/api/v1/bookmark/`
- **Method**: `POST`
- **Authentication**: Required
- **Request Body**:
  ```json
  {
    "content_type_id": 1,
    "object_id": 5
  }
  ```
- **Success Response**: 
  ```json
  {
    "id": 1,
    "user": {
      "id": 1,
      "username": "username",
      "avatar_url": "https://example.com/media/avatars/user.jpg",
      "full_name": "User Name",
      "is_verified": true
    },
    "created_at": "2023-05-18T12:00:00Z"
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If content type ID or object ID is invalid, or if the user has already bookmarked this content.
  - `404 Not Found`: If content type or object doesn't exist.

### Get Bookmark Details

Retrieves details of a specific bookmark.

- **URL**: `/api/v1/bookmark/{id}/`
- **Method**: `GET`
- **Authentication**: Required
- **Success Response**: 
  ```json
  {
    "id": 1,
    "user": {
      "id": 1,
      "username": "username",
      "avatar_url": "https://example.com/media/avatars/user.jpg",
      "full_name": "User Name",
      "is_verified": true
    },
    "created_at": "2023-05-18T12:00:00Z"
  }
  ```
- **Error Response**: `404 Not Found` if bookmark doesn't exist.

### Delete Bookmark

Deletes a specific bookmark.

- **URL**: `/api/v1/bookmark/{id}/`
- **Method**: `DELETE`
- **Authentication**: Required
- **Success Response**: `204 No Content`
- **Error Response**: `404 Not Found` if bookmark doesn't exist or user doesn't own the bookmark.

### Toggle Bookmark

Toggles the bookmark status for a content object (adds bookmark if not bookmarked, removes if already bookmarked).

- **URL**: `/api/v1/bookmark/toggle/`
- **Method**: `POST`
- **Authentication**: Required
- **Request Body**:
  ```json
  {
    "content_type_id": 1,
    "object_id": 5
  }
  ```
- **Success Response (Add)**:
  ```json
  {
    "detail": "Bookmark added.",
    "bookmarked": true,
    "data": {
      "id": 1,
      "user": {
        "id": 1,
        "username": "username",
        "avatar_url": "https://example.com/media/avatars/user.jpg",
        "full_name": "User Name",
        "is_verified": true
      },
      "created_at": "2023-05-18T12:00:00Z"
    }
  }
  ```
- **Success Response (Remove)**:
  ```json
  {
    "detail": "Bookmark removed.",
    "bookmarked": false
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If content type ID or object ID is invalid or missing.
  - `404 Not Found`: If content type or object doesn't exist.

### Check Bookmark Status

Checks if the current user has bookmarked a specific content object.

- **URL**: `/api/v1/bookmark/check/`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `content_type_id`: Content type ID
  - `object_id`: Object ID
- **Success Response**:
  ```json
  {
    "bookmarked": true
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: If content type ID or object ID is invalid or missing.
  - `404 Not Found`: If content type or object doesn't exist.

### Get User's Bookmarks

Retrieves all bookmarks created by the current authenticated user.

- **URL**: `/api/v1/bookmark/my_bookmarks/`
- **Method**: `GET`
- **Authentication**: Required
- **Success Response**:
  ```json
  [
    {
      "id": 1,
      "user": {
        "id": 1,
        "username": "username",
        "avatar_url": "https://example.com/media/avatars/user.jpg",
        "full_name": "User Name",
        "is_verified": true
      },
      "created_at": "2023-05-18T12:00:00Z"
    }
  ]
  ```

## Error Handling

All endpoints may return the following errors:

- `401 Unauthorized`: If authentication is missing or invalid
- `403 Forbidden`: If user doesn't have permission to perform the action
- `500 Internal Server Error`: If there's a server-side error

## Examples

### Example: Bookmark a post

```http
POST /api/v1/bookmark/
Content-Type: application/json
Authorization: Token your_auth_token

{
  "content_type_id": 7,  // ID for the "post" content type
  "object_id": 42        // ID of the post to bookmark
}
```

### Example: Check if a post is bookmarked

```http
GET /api/v1/bookmark/check/?content_type_id=7&object_id=42
Authorization: Token your_auth_token
```

### Example: Get all of the user's bookmarks

```http
GET /api/v1/bookmark/my_bookmarks/
Authorization: Token your_auth_token
```
