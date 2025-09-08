# Session Management Implementation

## Overview

This implementation provides persistent session management for the UTAS Writing Practice application using HTTP-only cookies. Each user gets a unique session ID that persists across browser sessions and page reloads.

## Architecture

```
Frontend Component → useSession Hook → Session API → HTTP-only Cookie
                                    ↓
                  Chat API ← Session ID ← Cookie Parser
```

## Key Components

### 1. Session Utility (`/src/lib/session.ts`)

Core session management functions:
- `generateSessionId()` - Creates unique session IDs
- `getOrCreateSessionId()` - Gets existing or creates new session
- `setSessionCookie()` - Sets HTTP-only cookie
- `createSessionResponse()` - Creates response with session cookie

### 2. Session API (`/src/app/api/session/route.ts`)

RESTful endpoints for session management:
- `GET /api/session` - Get current session or create new one
- `POST /api/session` - Force create new session
- `DELETE /api/session` - Clear current session

### 3. Session Hook (`/src/hooks/useSession.ts`)

React hook for frontend session management:
- Automatic session initialization
- Session state management
- Error handling
- Session refresh/clear functions

### 4. Updated Chat API (`/src/app/api/chat/route.ts`)

Enhanced chat API with session support:
- Automatic session ID extraction from cookies
- Session ID passed to AI Core service
- Session info included in responses

### 5. Updated ChatBox Component (`/src/components/ChatBox.tsx`)

Enhanced chat interface:
- Session status indicators
- Automatic session management
- Disabled state when no session

## Session ID Format

```
session_[32-character-hex-string]
Example: session_a1b2c3d4e5f6789012345678901234567890abcd
```

## Cookie Configuration

```javascript
{
  name: 'utas-session-id',
  maxAge: 30 * 24 * 60 * 60, // 30 days
  httpOnly: true,             // Secure, not accessible via JavaScript
  secure: true,               // HTTPS only in production
  sameSite: 'lax',           // CSRF protection
  path: '/'                   // Available site-wide
}
```

## Usage Examples

### Frontend Usage

```typescript
import { useSession } from '@/hooks/useSession';

function MyComponent() {
  const { sessionId, isLoading, error } = useSession();
  
  if (isLoading) return <div>Loading session...</div>;
  if (error) return <div>Session error: {error}</div>;
  
  return <div>Session ID: {sessionId}</div>;
}
```

### API Usage

```typescript
// In API route
import { getOrCreateSessionId, createSessionResponse } from '@/lib/session';

export async function POST(request: NextRequest) {
  const { sessionId, isNew } = getOrCreateSessionId(request);
  
  // Use sessionId for your logic
  const result = await processWithSession(sessionId);
  
  // Return response with session cookie
  return createSessionResponse(result, sessionId);
}
```

## Testing

### Test Page

Visit `/test-session` to test session functionality:
- View current session information
- Test session API endpoints
- Test chat API with session
- Monitor session persistence

### Manual Testing

1. **Session Creation**:
   ```bash
   curl -c cookies.txt http://localhost:3000/api/session
   ```

2. **Session Usage**:
   ```bash
   curl -b cookies.txt -X POST http://localhost:3000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello"}'
   ```

3. **Session Clearing**:
   ```bash
   curl -b cookies.txt -X DELETE http://localhost:3000/api/session
   ```

## Security Features

### HTTP-Only Cookies
- Not accessible via JavaScript
- Prevents XSS attacks
- Automatic inclusion in requests

### Secure Configuration
- HTTPS-only in production
- SameSite protection against CSRF
- 30-day expiration

### Session Validation
- Format validation for session IDs
- Error handling for invalid sessions
- Automatic session regeneration

## Benefits

### User Experience
- **Persistent Sessions**: Survives page reloads and browser restarts
- **Seamless Integration**: Automatic session management
- **Error Recovery**: Graceful handling of session issues

### Developer Experience
- **Simple API**: Easy-to-use hooks and utilities
- **Type Safety**: Full TypeScript support
- **Debugging**: Comprehensive logging and test tools

### Security
- **HTTP-Only**: Secure cookie storage
- **Validation**: Session ID format validation
- **Expiration**: Automatic cleanup of old sessions

## Migration from Header-Based

### Before (Header-based)
```typescript
// Manual session ID in header
const response = await fetch('/api/chat', {
  headers: {
    'x-conversation-id': 'manual-session-id'
  }
});
```

### After (Cookie-based)
```typescript
// Automatic session management
const response = await fetch('/api/chat', {
  credentials: 'include' // Includes cookies automatically
});
```

## Monitoring

### Session Metrics
- Session creation rate
- Session duration
- Error rates
- Cookie acceptance

### Debugging
- Session status in chat header
- Test page for manual testing
- Console logging for development
- Network tab shows cookie headers

## Future Enhancements

### Possible Improvements
1. **Session Analytics**: Track session usage patterns
2. **Session Cleanup**: Background cleanup of expired sessions
3. **Multi-Device Support**: Sync sessions across devices
4. **Session Storage**: Store session data in database
5. **Rate Limiting**: Per-session rate limiting

### Database Integration
```typescript
// Future: Store session data
interface SessionData {
  sessionId: string;
  userId?: string;
  createdAt: Date;
  lastUsed: Date;
  metadata: Record<string, any>;
}
```

## Troubleshooting

### Common Issues

1. **Session Not Persisting**
   - Check cookie settings in browser
   - Verify HTTPS in production
   - Check SameSite policy

2. **Session Errors**
   - Check session ID format
   - Verify cookie expiration
   - Check network connectivity

3. **Chat Not Working**
   - Verify session is loaded
   - Check API endpoints
   - Monitor network requests

### Debug Steps

1. Open browser DevTools
2. Check Application → Cookies
3. Look for `utas-session-id` cookie
4. Check Network tab for session requests
5. Use `/test-session` page for debugging
