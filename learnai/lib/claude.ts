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
