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
