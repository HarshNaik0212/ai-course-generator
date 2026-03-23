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
