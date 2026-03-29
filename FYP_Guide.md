# Backend Integration Guide - FastAPI to React Frontend

This guide shows you exactly where to connect your FastAPI backend to the frontend.

## 📁 API Service Layer

All API functions are centralized in: **`/src/app/services/api.ts`**

This file contains all the functions you need to call your FastAPI endpoints.

## 🔧 Configuration

### 1. Set Your Backend URL

Create a `.env` file in the root directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

Or for production:

```env
REACT_APP_API_URL=https://your-backend-api.com
```

### 2. Install Axios (Optional but Recommended)

If you prefer using Axios instead of fetch:

```bash
npm install axios
```

Then replace the `apiRequest` function in `/src/app/services/api.ts` with Axios.

## 📍 Files to Modify & What to Connect

### 1. **Authentication** - `/src/app/context/AppContext.tsx`

**Current:** Mock users stored in memory (lines 33-37)
**What to replace:** `login()` and `register()` functions

```typescript
// REPLACE THIS SECTION (lines 50-81)

// Current mock login:
const login = (username: string, password: string): boolean => {
  if (username === MOCK_ADMIN.username && password === MOCK_ADMIN.password) {
    setUser({ username, role: 'admin' });
    return true;
  }
  // ... more mock logic
};

// REPLACE WITH:
import { login as apiLogin, register as apiRegister, setAuthToken } from '../services/api';

const login = async (username: string, password: string): Promise<boolean> => {
  try {
    const response = await apiLogin({ username, password });
    setUser({
      username: response.username,
      name: response.name,
      email: response.email,
      role: response.role
    });
    
    // If using JWT tokens
    if (response.token) {
      setAuthToken(response.token);
    }
    
    return true;
  } catch (error) {
    console.error('Login failed:', error);
    return false;
  }
};

const register = async (data: { name: string; email: string; username: string; password: string }): Promise<boolean> => {
  try {
    const response = await apiRegister(data);
    return response.success;
  } catch (error) {
    console.error('Registration failed:', error);
    return false;
  }
};
```

**FastAPI endpoints needed:**
- `POST /api/auth/login` - Accept username & password, return user data + role
- `POST /api/auth/register` - Accept user data, create account

---

### 2. **Search & Analysis** - `/src/app/pages/UserSearchPage.tsx`

**Current:** Mock validation logic (lines 70-80)
**What to replace:** `handleSearch()` function

```typescript
// REPLACE THIS SECTION (lines 68-90)

// Current mock search:
const handleSearch = () => {
  // ... validation
  addSearchHistory(query, currentCategory || 'general', selectedPlatforms);
  navigate('/results', { state: { query, category: currentCategory, platforms: selectedPlatforms } });
};

// REPLACE WITH:
import { validateSearch } from '../services/api';

const handleSearch = async () => {
  setError('');

  if (!query.trim()) {
    setError('Please enter a product name');
    return;
  }

  if (selectedPlatforms.length === 0) {
    setError('Please select at least one review platform');
    return;
  }

  // Optional: Validate with backend before proceeding
  try {
    const validation = await validateSearch({
      query,
      category: currentCategory || 'general',
      platforms: selectedPlatforms
    });
    
    if (!validation.valid) {
      setError(validation.message || 'Invalid search query');
      return;
    }
  } catch (error) {
    setError('Failed to validate search. Please try again.');
    return;
  }

  addSearchHistory(query, currentCategory || 'general', selectedPlatforms);
  navigate('/results', { state: { query, category: currentCategory, platforms: selectedPlatforms } });
};
```

**FastAPI endpoints needed:**
- `POST /api/reviews/validate` - Validate search query before analysis

---

### 3. **Results Page** - `/src/app/pages/UserResultsPage.tsx`

**Current:** Mock data generator (lines 28-90)
**What to replace:** `generateMockData()` function call

```typescript
// REPLACE THIS SECTION (around line 91)

// Current mock data:
const data = generateMockData(state.query);

// REPLACE WITH:
import { analyzeReviews, AnalysisResult } from '../services/api';
import { useEffect, useState } from 'react';

export function UserResultsPage() {
  // ... existing code
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchAnalysis() {
      try {
        setLoading(true);
        const result = await analyzeReviews({
          query: state.query,
          category: state.category || 'general',
          platforms: state.platforms
        });
        setData(result);
      } catch (error) {
        console.error('Failed to fetch analysis:', error);
        setError('Failed to load analysis. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    fetchAnalysis();
  }, [state.query, state.category, state.platforms]);

  if (loading) {
    return <div>Loading analysis...</div>;
  }

  if (error || !data) {
    return <div>Error: {error || 'No data available'}</div>;
  }

  // ... rest of component using {data}
}
```

**FastAPI endpoints needed:**
- `POST /api/reviews/analyze` - Accept query, category, platforms. Return full analysis data

---

### 4. **Admin Logs** - `/src/app/pages/AdminLogsPage.tsx`

**Current:** Mock logs array (line 13-85)
**What to replace:** `MOCK_LOGS` constant

```typescript
// REPLACE THIS SECTION (lines 88+)

// Current mock:
const [logs] = useState<LogEntry[]>(MOCK_LOGS);

// REPLACE WITH:
import { getLogs } from '../services/api';

export function AdminLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterLevel, setFilterLevel] = useState<string>('all');

  useEffect(() => {
    async function fetchLogs() {
      try {
        setLoading(true);
        const data = await getLogs({ level: filterLevel });
        setLogs(data);
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchLogs();
  }, [filterLevel]);

  // ... rest of component
}
```

**FastAPI endpoints needed:**
- `GET /api/admin/logs?level={level}` - Return system logs

---

### 5. **Admin Users** - `/src/app/pages/AdminUsersPage.tsx`

**Current:** Mock users array (line 14-62)
**What to replace:** `INITIAL_USERS` constant and CRUD operations

```typescript
// REPLACE INITIAL DATA AND CRUD OPERATIONS

import { getUsers, addUser, updateUser, deleteUser } from '../services/api';

export function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch users on mount
  useEffect(() => {
    async function fetchUsers() {
      try {
        setLoading(true);
        const data = await getUsers();
        setUsers(data);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchUsers();
  }, []);

  // Handle add user
  const handleAddUser = async (userData: Omit<User, 'id'>) => {
    try {
      const newUser = await addUser(userData);
      setUsers([...users, newUser]);
    } catch (error) {
      console.error('Failed to add user:', error);
    }
  };

  // Handle update user
  const handleUpdateUser = async (userId: string, userData: Partial<User>) => {
    try {
      const updatedUser = await updateUser(userId, userData);
      setUsers(users.map(u => u.id === userId ? updatedUser : u));
    } catch (error) {
      console.error('Failed to update user:', error);
    }
  };

  // Handle delete user
  const handleDeleteUser = async (userId: string) => {
    try {
      await deleteUser(userId);
      setUsers(users.filter(u => u.id !== userId));
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  // ... rest of component
}
```

**FastAPI endpoints needed:**
- `GET /api/admin/users` - Return all users
- `POST /api/admin/users` - Create new user
- `PUT /api/admin/users/{userId}` - Update user
- `DELETE /api/admin/users/{userId}` - Delete user

---

### 6. **Admin Sources** - `/src/app/pages/AdminSourcesPage.tsx`

**Current:** Mock sources array (line 16-81)
**What to replace:** `INITIAL_SOURCES` constant and operations

```typescript
// REPLACE SIMILAR TO USERS PAGE

import { getSources, updateSource, checkSourceStatus } from '../services/api';

export function AdminSourcesPage() {
  const [sources, setSources] = useState<ReviewSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSources() {
      try {
        setLoading(true);
        const data = await getSources();
        setSources(data);
      } catch (error) {
        console.error('Failed to fetch sources:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchSources();
  }, []);

  const handleCheckStatus = async (sourceId: string) => {
    try {
      const updatedSource = await checkSourceStatus(sourceId);
      setSources(sources.map(s => s.id === sourceId ? updatedSource : s));
    } catch (error) {
      console.error('Failed to check source status:', error);
    }
  };

  // ... rest of component
}
```

**FastAPI endpoints needed:**
- `GET /api/admin/sources` - Return all review sources
- `PUT /api/admin/sources/{sourceId}` - Update source
- `POST /api/admin/sources/{sourceId}/check` - Check source status

---

## 🎯 Summary of Required FastAPI Endpoints

### Authentication
- `POST /api/auth/login`
- `POST /api/auth/register`

### Review Analysis
- `POST /api/reviews/validate`
- `POST /api/reviews/analyze`

### Admin - Logs
- `GET /api/admin/logs`

### Admin - Users
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{userId}`
- `DELETE /api/admin/users/{userId}`

### Admin - Sources
- `GET /api/admin/sources`
- `PUT /api/admin/sources/{sourceId}`
- `POST /api/admin/sources/{sourceId}/check`

---

## 🔐 CORS Configuration (FastAPI)

Make sure your FastAPI backend has CORS enabled:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚀 Testing the Integration

1. Start your FastAPI backend: `uvicorn main:app --reload`
2. Start your React frontend: `npm start`
3. Test each feature one by one:
   - Login/Register
   - Search validation
   - Review analysis
   - Admin pages (logs, users, sources)

---

## 💡 Tips

1. **Error Handling**: All API functions in `api.ts` throw errors. Use try-catch blocks.
2. **Loading States**: Add loading spinners while fetching data
3. **JWT Tokens**: If using JWT, the token helpers are already in `api.ts`
4. **Type Safety**: All TypeScript interfaces match the expected API responses
5. **Environment Variables**: Use `.env` for different environments (dev, staging, prod)

---

## 📝 Example FastAPI Response Formats

### Login Response
```json
{
  "username": "demo",
  "name": "Demo User",
  "email": "demo@example.com",
  "role": "user",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Analysis Response
```json
{
  "summary": "Based on analysis of over 2,500 reviews...",
  "pros": ["Excellent build quality", "Great performance"],
  "cons": ["Expensive", "Limited storage"],
  "sentimentData": [
    {"name": "Positive", "value": 72, "color": "#10b981"},
    {"name": "Neutral", "value": 18, "color": "#6b7280"},
    {"name": "Negative", "value": 10, "color": "#ef4444"}
  ],
  "ratingData": [
    {"rating": "5 Stars", "count": 1250, "percentage": 50}
  ],
  "trendData": [
    {"month": "Jan", "positive": 45, "negative": 10, "neutral": 15}
  ],
  "topicsData": [
    {"topic": "Performance", "mentions": 1200}
  ]
}
```
