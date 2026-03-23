# LearnAI Backend Documentation

Complete backend architecture and API documentation for recreating the backend.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Endpoints](#api-endpoints)
3. [Data Models](#data-models)
4. [AI Integration Details](#ai-integration-details)
5. [Business Logic](#business-logic)
6. [Required Backend Endpoints](#required-backend-endpoints)
7. [Database Schema](#database-schema)
8. [Current Implementation Files](#current-implementation-files)
9. [Environment Variables](#environment-variables)
10. [Suggested Backend Structure](#suggested-backend-structure)

---

## Architecture Overview

The application uses a **hybrid architecture**:
- **Frontend**: Next.js 15 with React 19 (App Router)
- **Backend**: Next.js API Routes (serverless functions)
- **Data Persistence**: localStorage (client-side) - **needs backend replacement**
- **AI Integration**: Anthropic Claude API (claude-sonnet-4-20250514)

### Current State
- **Only 1 API route exists**: `/api/chat` (proxies to Anthropic Claude)
- **No database**: All data stored in browser localStorage via Zustand
- **No authentication backend**: Using Clerk (third-party service)

---

## API Endpoints

### Chat API - `/api/chat/route.ts`

**Endpoint**: `POST /api/chat`

**Purpose**: Handles all AI interactions - course generation and chat conversations

**Request Body**:
```typescript
{
  messages: Array<{ role: 'user' | 'assistant', content: string }>,
  systemPrompt: string,
  stream?: boolean,           // Enable SSE streaming
  isCourseGeneration?: boolean // Uses higher token limit
}
```

**Response (non-streaming)**:
```json
{
  "content": "AI response text",
  "usage": { "input_tokens": N, "output_tokens": N }
}
```

**Response (streaming)**: Server-Sent Events (SSE)
```
data: {"content": "chunk"}
data: {"content": "chunk"}
data: [DONE]
```

---

## Data Models

### Course
```typescript
interface Course {
  id: string;                    // Unique identifier
  courseName: string;            // Display name
  createdAt: string;             // ISO timestamp
  totalWeeks: number;            // 1-8 weeks
  skillLevel?: 'Beginner' | 'Intermediate' | 'Advanced';
  weeks: Week[];
}
```

### Week
```typescript
interface Week {
  weekNumber: number;
  weekTitle: string;
  days: Day[];
}
```

### Day
```typescript
interface Day {
  dayNumber: number;
  dayTitle: string;
  topics: string[];
  studyContent: string;          // Markdown content (400-600 words)
  quiz: QuizQuestion[];
  isCompleted: boolean;
  quizScore?: number;            // 0-100
  isUnlocked: boolean;           // Day 1 always unlocked
}
```

### QuizQuestion
```typescript
interface QuizQuestion {
  question: string;
  options: [string, string, string, string]; // 4 options
  correctAnswer: number;         // Index 0-3
}
```

### ChatSession
```typescript
interface ChatSession {
  id: string;
  courseId: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}
```

### ChatMessage
```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
```

### CourseProgress
```typescript
interface CourseProgress {
  courseId: string;
  completedDays: number;
  totalDays: number;
  percentage: number;
  averageScore: number;
  certificateEarned: boolean;
}
```

### ClaudeMessage
```typescript
interface ClaudeMessage {
  role: 'user' | 'assistant';
  content: string;
}
```

### CourseGenerationInput
```typescript
interface CourseGenerationInput {
  topic: string;
  weeks?: number;
  skillLevel?: 'Beginner' | 'Intermediate' | 'Advanced';
}
```

---

## AI Integration Details

### Claude Model
- **Model**: `claude-sonnet-4-20250514`
- **API URL**: `https://api.anthropic.com/v1/messages`
- **API Version**: `2023-06-01`

### Course Generation System Prompt
```
You are a curriculum designer. Generate a structured course plan in JSON format only. 
The JSON must follow this exact schema:
{
  "courseName": string,
  "totalWeeks": number,
  "weeks": [
    {
      "weekNumber": number,
      "weekTitle": string,
      "days": [
        {
          "dayNumber": number,
          "dayTitle": string,
          "topics": string[],
          "studyContent": string (detailed markdown content for this day, 400-600 words with code examples where relevant),
          "quiz": [
            {
              "question": string,
              "options": [string, string, string, string],
              "correctAnswer": number (0-3 index)
            }
          ]
        }
      ]
    }
  ]
}

Generate exactly 5 MCQ questions per day. Study content should be rich markdown content with headings, bullet points, and code examples where relevant. 
Return ONLY valid JSON, no markdown wrapper, no explanation.
```

### Chat Tutor System Prompt
```
You are an expert educational AI tutor. The user is learning {courseName}. Help them understand concepts, answer doubts, and explain topics clearly with examples. Be encouraging, concise, and use code examples when helpful. Format your responses using markdown for better readability.
```

### Token Limits
- **Course Generation**: 16,000 tokens (non-streaming)
- **Chat Conversations**: 4,096 tokens (streaming enabled)

---

## Business Logic

### Day Unlocking Logic
1. **Day 1** is always unlocked by default
2. **Day N+1** unlocks ONLY after Day N's quiz is completed
3. Quiz completion = User submitted answers (regardless of score)

```typescript
// Day unlocking logic
function unlockNextDay(courseId, currentWeek, currentDay) {
  const nextDay = findNextDay(currentWeek, currentDay);
  if (nextDay) {
    nextDay.isUnlocked = true;
  }
}
```

### Progress Calculation
```typescript
// Course progress percentage
function calculateProgress(courseId) {
  const { completed, total } = countCompletedDays(courseId);
  return Math.round((completed / total) * 100);
}

// Average quiz score
function calculateAverageScore(courseId) {
  const scores = getAllQuizScores(courseId);
  return scores.length > 0 
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) 
    : 0;
}

// Certificate eligibility
function checkCertificate(courseId) {
  const progress = calculateProgress(courseId);
  const avgScore = calculateAverageScore(courseId);
  return progress === 100 && avgScore >= 50;
}
```

### Certificate Requirements
- **Progress**: 100% (all days completed)
- **Average Score**: ≥ 50% across all quizzes

---

## Required Backend Endpoints

Your friend should create these REST API endpoints:

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | User registration |
| `POST` | `/api/auth/login` | User login |
| `POST` | `/api/auth/logout` | User logout |
| `GET` | `/api/auth/me` | Get current user |

### Courses
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/courses` | Create course (AI generation) |
| `GET` | `/api/courses` | List user's courses |
| `GET` | `/api/courses/:id` | Get course details |
| `DELETE` | `/api/courses/:id` | Delete course |

### Progress
| Method | Endpoint | Description |
|--------|----------|-------------|
| `PATCH` | `/api/courses/:id/days/:dayId` | Update day progress |
| `POST` | `/api/courses/:id/quiz` | Submit quiz answers |
| `GET` | `/api/courses/:id/progress` | Get progress stats |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Chat with AI (streaming) |
| `GET` | `/api/courses/:id/sessions` | List chat sessions |
| `POST` | `/api/sessions` | Create new chat session |
| `GET` | `/api/sessions/:id` | Get session with messages |
| `DELETE` | `/api/sessions/:id` | Delete session |

### Certificates
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/courses/:id/certificate` | Download certificate |

---

## Database Schema

### PostgreSQL Schema

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Courses
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  name VARCHAR(255) NOT NULL,
  skill_level VARCHAR(20) CHECK (skill_level IN ('Beginner', 'Intermediate', 'Advanced')),
  total_weeks INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Weeks
CREATE TABLE weeks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE NOT NULL,
  week_number INTEGER NOT NULL,
  title VARCHAR(255) NOT NULL,
  UNIQUE(course_id, week_number)
);

-- Days
CREATE TABLE days (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  week_id UUID REFERENCES weeks(id) ON DELETE CASCADE NOT NULL,
  day_number INTEGER NOT NULL,
  title VARCHAR(255) NOT NULL,
  topics JSONB NOT NULL DEFAULT '[]',
  study_content TEXT NOT NULL,
  is_unlocked BOOLEAN DEFAULT false,
  is_completed BOOLEAN DEFAULT false,
  quiz_score INTEGER CHECK (quiz_score >= 0 AND quiz_score <= 100),
  UNIQUE(week_id, day_number)
);

-- Quizzes
CREATE TABLE quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  day_id UUID REFERENCES days(id) ON DELETE CASCADE NOT NULL UNIQUE,
  questions JSONB NOT NULL
);

-- Quiz Attempts (for tracking)
CREATE TABLE quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  day_id UUID REFERENCES days(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  score INTEGER NOT NULL,
  answers JSONB NOT NULL,
  submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Sessions
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  title VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Messages
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Certificates
CREATE TABLE certificates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  issued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  certificate_url VARCHAR(500),
  UNIQUE(course_id, user_id)
);

-- Indexes for performance
CREATE INDEX idx_courses_user_id ON courses(user_id);
CREATE INDEX idx_weeks_course_id ON weeks(course_id);
CREATE INDEX idx_days_week_id ON days(week_id);
CREATE INDEX idx_chat_sessions_course_id ON chat_sessions(course_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
```

### Prisma Schema Alternative

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String         @id @default(uuid())
  email         String         @unique
  passwordHash  String
  firstName     String?
  lastName      String?
  courses       Course[]
  chatSessions  ChatSession[]
  certificates  Certificate[]
  createdAt     DateTime       @default(now())
  updatedAt     DateTime       @updatedAt

  @@map("users")
}

model Course {
  id           String         @id @default(uuid())
  name         String
  skillLevel   String?
  totalWeeks   Int
  userId       String
  user         User           @relation(fields: [userId], references: [id], onDelete: Cascade)
  weeks        Week[]
  chatSessions ChatSession[]
  certificate  Certificate?
  createdAt    DateTime       @default(now())
  updatedAt    DateTime       @updatedAt

  @@map("courses")
}

model Week {
  id         String   @id @default(uuid())
  weekNumber Int
  title      String
  courseId   String
  course     Course   @relation(fields: [courseId], references: [id], onDelete: Cascade)
  days       Day[]

  @@unique([courseId, weekNumber])
  @@map("weeks")
}

model Day {
  id           String    @id @default(uuid())
  dayNumber    Int
  title        String
  topics       Json
  studyContent String
  isUnlocked   Boolean   @default(false)
  isCompleted  Boolean   @default(false)
  quizScore    Int?
  weekId       String
  week         Week      @relation(fields: [weekId], references: [id], onDelete: Cascade)
  quiz         Quiz?

  @@unique([weekId, dayNumber])
  @@map("days")
}

model Quiz {
  id        String @id @default(uuid())
  questions Json
  dayId     String @unique
  day       Day    @relation(fields: [dayId], references: [id], onDelete: Cascade)

  @@map("quizzes")
}

model ChatSession {
  id        String        @id @default(uuid())
  title     String
  courseId  String
  course    Course        @relation(fields: [courseId], references: [id], onDelete: Cascade)
  userId    String
  user      User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  messages  ChatMessage[]
  createdAt DateTime      @default(now())
  updatedAt DateTime      @updatedAt

  @@map("chat_sessions")
}

model ChatMessage {
  id        String      @id @default(uuid())
  role      String
  content   String
  sessionId String
  session   ChatSession @relation(fields: [sessionId], references: [id], onDelete: Cascade)
  createdAt DateTime    @default(now())

  @@map("chat_messages")
}

model Certificate {
  id             String   @id @default(uuid())
  courseId       String   @unique
  course         Course   @relation(fields: [courseId], references: [id], onDelete: Cascade)
  userId         String
  user           User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  certificateUrl String?
  issuedAt       DateTime @default(now())

  @@unique([courseId, userId])
  @@map("certificates")
}
```

---

## Current Implementation Files

### API Route: `/app/api/chat/route.ts`

```typescript
import { NextRequest } from 'next/server';

const CLAUDE_MODEL = 'claude-sonnet-4-20250514';
const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatRequest {
  messages: Message[];
  systemPrompt: string;
  stream?: boolean;
  isCourseGeneration?: boolean;
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { messages, systemPrompt, stream = true, isCourseGeneration = false } = body;

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      return Response.json({ error: 'ANTHROPIC_API_KEY not configured' }, { status: 500 });
    }

    // For course generation, we need more tokens and no streaming
    const maxTokens = isCourseGeneration ? 16000 : 4096;
    const shouldStream = isCourseGeneration ? false : stream;

    const response = await fetch(ANTHROPIC_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
      },
      body: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: maxTokens,
        system: systemPrompt,
        messages: messages,
        stream: shouldStream
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Claude API error:', errorData);
      return Response.json(
        { error: errorData.error?.message || `API error: ${response.status}` },
        { status: response.status }
      );
    }

    if (shouldStream) {
      // Stream response
      const encoder = new TextEncoder();
      const reader = response.body?.getReader();
      
      if (!reader) {
        return Response.json({ error: 'No response body' }, { status: 500 });
      }

      const stream = new ReadableStream({
        async start(controller) {
          const decoder = new TextDecoder();
          
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split('\n');
              
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6);
                  if (data === '[DONE]') {
                    controller.enqueue(encoder.encode('data: [DONE]\n\n'));
                    continue;
                  }
                  
                  try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
                      const outData = JSON.stringify({ content: parsed.delta.text });
                      controller.enqueue(encoder.encode(`data: ${outData}\n\n`));
                    }
                  } catch {
                    // Skip invalid JSON
                  }
                }
              }
            }
            controller.close();
          } catch (error) {
            controller.error(error);
          }
        }
      });

      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        }
      });
    } else {
      // Non-streaming response
      const data = await response.json();
      
      // Extract text content from the response
      let content = '';
      if (data.content && Array.isArray(data.content)) {
        for (const block of data.content) {
          if (block.type === 'text') {
            content += block.text;
          }
        }
      }
      
      return Response.json({ content, usage: data.usage });
    }
  } catch (error) {
    console.error('Chat API error:', error);
    return Response.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
```

### AI Helper: `/lib/claude.ts`

```typescript
import type { Course, ClaudeMessage, CourseGenerationInput } from '@/types';

const CLAUDE_MODEL = 'claude-sonnet-4-20250514';

export async function generateCourse(input: CourseGenerationInput): Promise<Course> {
  const systemPrompt = `You are a curriculum designer. Generate a structured course plan in JSON format only. 
The JSON must follow this exact schema:
{
  "courseName": string,
  "totalWeeks": number,
  "weeks": [
    {
      "weekNumber": number,
      "weekTitle": string,
      "days": [
        {
          "dayNumber": number,
          "dayTitle": string,
          "topics": string[],
          "studyContent": string (detailed markdown content for this day, 400-600 words with code examples where relevant),
          "quiz": [
            {
              "question": string,
              "options": [string, string, string, string],
              "correctAnswer": number (0-3 index)
            }
          ]
        }
      ]
    }
  ]
}

Generate exactly 5 MCQ questions per day. Study content should be rich markdown content with headings, bullet points, and code examples where relevant. 
Return ONLY valid JSON, no markdown wrapper, no explanation.`;

  const userPrompt = `Create a course for: ${input.topic}
Duration: ${input.weeks || 4} weeks
Skill Level: ${input.skillLevel || 'Beginner'}

Generate the complete course structure following the schema exactly.`;

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: 'user', content: userPrompt }],
      systemPrompt,
      isCourseGeneration: true
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to generate course');
  }

  const data = await response.json();
  
  try {
    // Parse the course JSON from the response
    const courseData = JSON.parse(data.content);
    
    // Add IDs and initial state to the course
    const course: Course = {
      id: `course-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      courseName: courseData.courseName,
      createdAt: new Date().toISOString(),
      totalWeeks: courseData.totalWeeks,
      weeks: courseData.weeks.map((week: any) => ({
        weekNumber: week.weekNumber,
        weekTitle: week.weekTitle,
        days: week.days.map((day: any, dayIndex: number) => ({
          dayNumber: day.dayNumber,
          dayTitle: day.dayTitle,
          topics: day.topics,
          studyContent: day.studyContent,
          quiz: day.quiz,
          isCompleted: false,
          quizScore: undefined,
          isUnlocked: week.weekNumber === 1 && dayIndex === 0 // Only first day is unlocked
        }))
      })),
      skillLevel: input.skillLevel
    };
    
    return course;
  } catch (e) {
    console.error('Failed to parse course JSON:', e);
    throw new Error('Failed to parse course data');
  }
}

export async function* chatWithAI(
  messages: ClaudeMessage[],
  courseName: string
): AsyncGenerator<string> {
  const systemPrompt = `You are an expert educational AI tutor. The user is learning ${courseName}. Help them understand concepts, answer doubts, and explain topics clearly with examples. Be encouraging, concise, and use code examples when helpful. Format your responses using markdown for better readability.`;

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      systemPrompt,
      stream: true
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get AI response');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    
    // Process SSE events
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') continue;
        
        try {
          const parsed = JSON.parse(data);
          if (parsed.content) {
            yield parsed.content;
          }
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}

export async function chatWithAISimple(
  messages: ClaudeMessage[],
  courseName: string
): Promise<string> {
  const systemPrompt = `You are an expert educational AI tutor. The user is learning ${courseName}. Help them understand concepts, answer doubts, and explain topics clearly with examples. Be encouraging, concise, and use code examples when helpful. Format your responses using markdown for better readability.`;

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      systemPrompt,
      stream: false
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get AI response');
  }

  const data = await response.json();
  return data.content;
}
```

### State Management: `/lib/store.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Course, ChatSession, ChatMessage } from '@/types';

interface AppState {
  courses: Course[];
  chatSessions: ChatSession[];
  activeCourseId: string | null;
  activeChatSessionId: string | null;
  isGeneratingCourse: boolean;
  
  // Course actions
  addCourse: (course: Course) => void;
  updateCourse: (courseId: string, updates: Partial<Course>) => void;
  deleteCourse: (courseId: string) => void;
  
  // Day progress actions
  updateDayProgress: (courseId: string, weekNum: number, dayNum: number, completed: boolean, quizScore?: number) => void;
  unlockDay: (courseId: string, weekNum: number, dayNum: number) => void;
  
  // Chat session actions
  addChatSession: (session: ChatSession) => void;
  updateChatSession: (sessionId: string, updates: Partial<ChatSession>) => void;
  deleteChatSession: (sessionId: string) => void;
  
  // Chat message actions
  addMessage: (sessionId: string, message: ChatMessage) => void;
  
  // Active state actions
  setActiveCourse: (courseId: string | null) => void;
  setActiveChatSession: (sessionId: string | null) => void;
  
  // Progress helpers
  getCourseProgress: (courseId: string) => number;
  getCourseAverageScore: (courseId: string) => number;
  getCourseCompletedDays: (courseId: string) => { completed: number; total: number };
  isCertificateEarned: (courseId: string) => boolean;
  
  // Generation state
  setIsGeneratingCourse: (isGenerating: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      courses: [],
      chatSessions: [],
      activeCourseId: null,
      activeChatSessionId: null,
      isGeneratingCourse: false,
      
      // Course actions
      addCourse: (course) => set((state) => ({
        courses: [...state.courses, course]
      })),
      
      updateCourse: (courseId, updates) => set((state) => ({
        courses: state.courses.map((c) =>
          c.id === courseId ? { ...c, ...updates } : c
        )
      })),
      
      deleteCourse: (courseId) => set((state) => ({
        courses: state.courses.filter((c) => c.id !== courseId),
        chatSessions: state.chatSessions.filter((s) => s.courseId !== courseId),
        activeCourseId: state.activeCourseId === courseId ? null : state.activeCourseId
      })),
      
      // Day progress actions
      updateDayProgress: (courseId, weekNum, dayNum, completed, quizScore) => set((state) => ({
        courses: state.courses.map((course) => {
          if (course.id !== courseId) return course;
          return {
            ...course,
            weeks: course.weeks.map((week) => {
              if (week.weekNumber !== weekNum) return week;
              return {
                ...week,
                days: week.days.map((day) => {
                  if (day.dayNumber !== dayNum) return day;
                  return { ...day, isCompleted: completed, quizScore };
                })
              };
            })
          };
        })
      })),
      
      unlockDay: (courseId, weekNum, dayNum) => set((state) => ({
        courses: state.courses.map((course) => {
          if (course.id !== courseId) return course;
          return {
            ...course,
            weeks: course.weeks.map((week) => {
              if (week.weekNumber !== weekNum) return week;
              return {
                ...week,
                days: week.days.map((day) => {
                  if (day.dayNumber !== dayNum) return day;
                  return { ...day, isUnlocked: true };
                })
              };
            })
          };
        })
      })),
      
      // Chat session actions
      addChatSession: (session) => set((state) => ({
        chatSessions: [...state.chatSessions, session]
      })),
      
      updateChatSession: (sessionId, updates) => set((state) => ({
        chatSessions: state.chatSessions.map((s) =>
          s.id === sessionId ? { ...s, ...updates } : s
        )
      })),
      
      deleteChatSession: (sessionId) => set((state) => ({
        chatSessions: state.chatSessions.filter((s) => s.id !== sessionId),
        activeChatSessionId: state.activeChatSessionId === sessionId ? null : state.activeChatSessionId
      })),
      
      // Chat message actions
      addMessage: (sessionId, message) => set((state) => ({
        chatSessions: state.chatSessions.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...s.messages, message] }
            : s
        )
      })),
      
      // Active state actions
      setActiveCourse: (courseId) => set({ activeCourseId: courseId }),
      setActiveChatSession: (sessionId) => set({ activeChatSessionId: sessionId }),
      
      // Progress helpers
      getCourseProgress: (courseId) => {
        const course = get().courses.find((c) => c.id === courseId);
        if (!course) return 0;
        
        let completedDays = 0;
        let totalDays = 0;
        
        course.weeks.forEach((week) => {
          week.days.forEach((day) => {
            totalDays++;
            if (day.isCompleted) completedDays++;
          });
        });
        
        return totalDays > 0 ? Math.round((completedDays / totalDays) * 100) : 0;
      },
      
      getCourseAverageScore: (courseId) => {
        const course = get().courses.find((c) => c.id === courseId);
        if (!course) return 0;
        
        let totalScore = 0;
        let completedQuizzes = 0;
        
        course.weeks.forEach((week) => {
          week.days.forEach((day) => {
            if (day.quizScore !== undefined) {
              totalScore += day.quizScore;
              completedQuizzes++;
            }
          });
        });
        
        return completedQuizzes > 0 ? Math.round(totalScore / completedQuizzes) : 0;
      },
      
      getCourseCompletedDays: (courseId) => {
        const course = get().courses.find((c) => c.id === courseId);
        if (!course) return { completed: 0, total: 0 };
        
        let completed = 0;
        let total = 0;
        
        course.weeks.forEach((week) => {
          week.days.forEach((day) => {
            total++;
            if (day.isCompleted) completed++;
          });
        });
        
        return { completed, total };
      },
      
      isCertificateEarned: (courseId) => {
        const progress = get().getCourseProgress(courseId);
        const avgScore = get().getCourseAverageScore(courseId);
        return progress === 100 && avgScore >= 50;
      },
      
      // Generation state
      setIsGeneratingCourse: (isGenerating) => set({ isGeneratingCourse: isGenerating })
    }),
    {
      name: 'learnai-storage',
      partialize: (state) => ({
        courses: state.courses,
        chatSessions: state.chatSessions,
        activeCourseId: state.activeCourseId,
        activeChatSessionId: state.activeChatSessionId
      })
    }
  )
);

// Helper function to generate unique IDs
export const generateId = () => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Helper to get current timestamp
export const getTimestamp = () => {
  return new Date().toISOString();
};
```

### TypeScript Types: `/types/index.ts`

```typescript
// Course Types
export interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
}

export interface Day {
  dayNumber: number;
  dayTitle: string;
  topics: string[];
  studyContent: string;
  quiz: QuizQuestion[];
  isCompleted: boolean;
  quizScore?: number;
  isUnlocked: boolean;
}

export interface Week {
  weekNumber: number;
  weekTitle: string;
  days: Day[];
}

export interface Course {
  id: string;
  courseName: string;
  createdAt: string;
  totalWeeks: number;
  weeks: Week[];
  skillLevel?: 'Beginner' | 'Intermediate' | 'Advanced';
}

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  courseId: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}

// Progress Types
export interface CourseProgress {
  courseId: string;
  completedDays: number;
  totalDays: number;
  percentage: number;
  averageScore: number;
  certificateEarned: boolean;
}

// API Types
export interface ClaudeMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface CourseGenerationInput {
  topic: string;
  weeks?: number;
  skillLevel?: 'Beginner' | 'Intermediate' | 'Advanced';
}
```

---

## Environment Variables

### Required for Current Implementation

```env
# AI Integration
ANTHROPIC_API_KEY=your_anthropic_api_key

# Clerk Authentication (optional - can be replaced)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
```

### Required for Full Backend

```env
# Backend Server
PORT=3001
NODE_ENV=development

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/learnai

# Authentication
JWT_SECRET=your_super_secret_jwt_key
JWT_EXPIRES_IN=7d

# AI Integration
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: Keep Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

# Optional: Email Service
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASS=your_password

# Optional: File Storage (for certificates)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=learnai-certificates
```

---

## Suggested Backend Structure

```
backend/
├── src/
│   ├── config/
│   │   ├── database.ts
│   │   ├── jwt.ts
│   │   └── anthropic.ts
│   ├── controllers/
│   │   ├── authController.ts
│   │   ├── courseController.ts
│   │   ├── chatController.ts
│   │   ├── progressController.ts
│   │   └── certificateController.ts
│   ├── middleware/
│   │   ├── auth.ts
│   │   ├── validate.ts
│   │   ├── errorHandler.ts
│   │   └── rateLimiter.ts
│   ├── models/
│   │   ├── User.ts
│   │   ├── Course.ts
│   │   ├── Week.ts
│   │   ├── Day.ts
│   │   ├── Quiz.ts
│   │   ├── ChatSession.ts
│   │   ├── ChatMessage.ts
│   │   └── Certificate.ts
│   ├── routes/
│   │   ├── index.ts
│   │   ├── auth.ts
│   │   ├── courses.ts
│   │   ├── chat.ts
│   │   ├── progress.ts
│   │   └── certificates.ts
│   ├── services/
│   │   ├── aiService.ts           # Claude API integration
│   │   ├── courseService.ts       # Course generation logic
│   │   ├── progressService.ts     # Progress calculations
│   │   └── certificateService.ts  # PDF generation
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   ├── validators.ts
│   │   ├── helpers.ts
│   │   └── constants.ts
│   └── app.ts
├── prisma/
│   ├── schema.prisma
│   └── migrations/
├── tests/
│   ├── unit/
│   └── integration/
├── .env.example
├── .gitignore
├── package.json
├── tsconfig.json
└── README.md
```

---

## Frontend Integration Changes

When the backend is ready, replace Zustand localStorage calls with API calls:

### Current (localStorage)
```typescript
const { courses, addCourse } = useAppStore();

// Create course
addCourse(newCourse);

// Get progress
const progress = getCourseProgress(courseId);
```

### Future (API)
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Fetch courses
const { data: courses } = useQuery({
  queryKey: ['courses'],
  queryFn: () => fetch('/api/courses').then(r => r.json())
});

// Create course
const createCourse = useMutation({
  mutationFn: (course) => fetch('/api/courses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(course)
  }),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['courses'] })
});

// Get progress
const { data: progress } = useQuery({
  queryKey: ['progress', courseId],
  queryFn: () => fetch(`/api/courses/${courseId}/progress`).then(r => r.json())
});
```

---

## Summary

### What Exists
1. Single API route `/api/chat` for AI communication
2. Client-side state management with Zustand + localStorage
3. TypeScript interfaces for all data models
4. AI helper functions for course generation and chat

### What Needs to Be Built
1. User authentication system
2. PostgreSQL database with proper schema
3. REST API endpoints for CRUD operations
4. Progress tracking on server
5. Certificate generation service
6. Chat session persistence

### Key Considerations
- **Day Unlocking**: Sequential unlocking based on quiz completion
- **Certificate**: Requires 100% progress + 50% average score
- **AI Integration**: Can remain on Next.js or move to backend
- **Streaming**: Chat uses SSE for real-time responses
