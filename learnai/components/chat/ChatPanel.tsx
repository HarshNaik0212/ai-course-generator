'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import type { SyntaxHighlighterProps } from 'react-syntax-highlighter';
// @ts-ignore
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAppStore, generateId, getTimestamp } from '@/lib/store';
import { generateCourse, chatWithAISimple } from '@/lib/claude';
import type { ChatMessage, Course, CourseGenerationInput } from '@/types';
import styles from './ChatPanel.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } }
};

const drawerVariants = {
  collapsed: { height: 40 },
  expanded: { height: 'auto' }
};

const loadingMessages = [
  'Analyzing your request...',
  'Building curriculum...',
  'Creating quiz questions...',
  'Finalizing course structure...'
];

interface ChatPanelProps {
  onTriggerNewCourse: boolean;
  onCourseGenerated?: () => void;
}

export default function ChatPanel({ onTriggerNewCourse, onCourseGenerated }: ChatPanelProps) {
  const { user } = useUser();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const {
    courses,
    chatSessions,
    activeCourseId,
    activeChatSessionId,
    addCourse,
    addMessage,
    setActiveCourse,
    setActiveChatSession,
    addChatSession,
    isGeneratingCourse,
    setIsGeneratingCourse
  } = useAppStore();

  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [courseTopic, setCourseTopic] = useState('');
  const [courseWeeks, setCourseWeeks] = useState('4');
  const [courseLevel, setCourseLevel] = useState<'Beginner' | 'Intermediate' | 'Advanced'>('Beginner');
  const [loadingStep, setLoadingStep] = useState(0);
  const [streamingMessage, setStreamingMessage] = useState('');

  const activeCourse = courses.find(c => c.id === activeCourseId);
  const activeSession = chatSessions.find(s => s.id === activeChatSessionId);

  useEffect(() => {
    if (onTriggerNewCourse) {
      setDrawerOpen(true);
    }
  }, [onTriggerNewCourse]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages, streamingMessage]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    const messageContent = input.trim();
    setInput('');

    // If no active session, create one
    let sessionId = activeChatSessionId;
    let courseId = activeCourseId;

    if (!sessionId && courseId) {
      const newSession = {
        id: `session-${Date.now()}`,
        courseId: courseId,
        title: messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : ''),
        createdAt: new Date().toISOString(),
        messages: []
      };
      addChatSession(newSession);
      sessionId = newSession.id;
      setActiveChatSession(sessionId);
    }

    if (!sessionId) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: messageContent,
      timestamp: getTimestamp()
    };
    addMessage(sessionId, userMessage);

    setIsSending(true);
    setStreamingMessage('');

    try {
      const courseName = activeCourse?.courseName || 'this topic';
      const messages = [...(activeSession?.messages || []), userMessage].map(m => ({
        role: m.role,
        content: m.content
      }));

      const response = await chatWithAISimple(messages, courseName);

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: response,
        timestamp: getTimestamp()
      };
      addMessage(sessionId, assistantMessage);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: getTimestamp()
      };
      addMessage(sessionId, errorMessage);
    } finally {
      setIsSending(false);
      setStreamingMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleGenerateCourse = async () => {
    if (!courseTopic.trim() || isGeneratingCourse) return;

    setIsGeneratingCourse(true);
    setDrawerOpen(false);

    // Start loading animation
    let step = 0;
    const loadingInterval = setInterval(() => {
      step = (step + 1) % loadingMessages.length;
      setLoadingStep(step);
    }, 2000);

    try {
      const input: CourseGenerationInput = {
        topic: courseTopic,
        weeks: parseInt(courseWeeks) || 4,
        skillLevel: courseLevel
      };

      const course = await generateCourse(input);
      addCourse(course);
      setActiveCourse(course.id);

      // Create a new chat session for this course
      const newSession = {
        id: `session-${Date.now()}`,
        courseId: course.id,
        title: `${course.courseName} - Getting Started`,
        createdAt: new Date().toISOString(),
        messages: []
      };
      addChatSession(newSession);
      setActiveChatSession(newSession.id);

      // Add welcome message
      const welcomeMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `✅ The course for **${course.courseName}** has been generated! You can start learning it from [Course Progress](/progress). Feel free to ask me any doubts about ${course.courseName}!`,
        timestamp: getTimestamp()
      };
      addMessage(newSession.id, welcomeMessage);

      setCourseTopic('');
      onCourseGenerated?.();
    } catch (error) {
      console.error('Course generation error:', error);
      alert('Failed to generate course. Please check your API key and try again.');
    } finally {
      clearInterval(loadingInterval);
      setIsGeneratingCourse(false);
      setLoadingStep(0);
    }
  };

  const getUserInitials = () => {
    if (!user) return '?';
    const firstName = user.firstName || '';
    const lastName = user.lastName || '';
    return (firstName[0] + lastName[0]).toUpperCase() || '?';
  };

  const showDrawer = !activeCourseId || courses.length === 0;

  return (
    <div className={styles.chatPanel}>
      {/* Greeting Bar */}
      <div className={styles.greetingBar}>
        <motion.h2
          className={styles.greeting}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Hello, {user?.firstName || 'there'}! 👋
        </motion.h2>
        <p className={styles.greetingSubtext}>What would you like to learn today?</p>
      </div>

      {/* Messages Area */}
      <div className={styles.messagesArea}>
        {activeSession?.messages.length === 0 && !isGeneratingCourse ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>💬</div>
            <h3 className={styles.emptyTitle}>Start a conversation</h3>
            <p className={styles.emptyText}>
              Ask questions about {activeCourse?.courseName || 'your course'} or generate a new course to begin learning.
            </p>
          </div>
        ) : (
          <>
            <AnimatePresence>
              {activeSession?.messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  className={`${styles.message} ${message.role === 'user' ? styles.messageUser : ''}`}
                  initial="hidden"
                  animate="visible"
                  variants={fadeUp}
                >
                  <div
                    className={`${styles.messageAvatar} ${
                      message.role === 'user' ? styles.messageAvatarUser : styles.messageAvatarAI
                    }`}
                  >
                    {message.role === 'user' ? getUserInitials() : '🤖'}
                  </div>
                  <div
                    className={`${styles.messageContent} ${
                      message.role === 'user' ? styles.messageContentUser : styles.messageContentAI
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code({ node, className, children, ...props }) {
                            const match = /language-(\w+)/.exec(className || '');
                            const isInline = !match;
                            return !isInline ? (
                              <SyntaxHighlighter
                                // @ts-ignore - style type incompatibility
                                style={vscDarkPlus}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            ) : (
                              <code className={className} {...props}>
                                {children}
                              </code>
                            );
                          }
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isSending && (
              <motion.div
                className={styles.message}
                initial="hidden"
                animate="visible"
                variants={fadeUp}
              >
                <div className={`${styles.messageAvatar} ${styles.messageAvatarAI}`}>🤖</div>
                <div className={styles.typingIndicator}>
                  <motion.span
                    className={styles.typingDot}
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity, delay: 0 }}
                  />
                  <motion.span
                    className={styles.typingDot}
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity, delay: 0.15 }}
                  />
                  <motion.span
                    className={styles.typingDot}
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity, delay: 0.3 }}
                  />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Course Generation Drawer */}
      <AnimatePresence>
        {showDrawer && (
          <motion.div
            className={styles.drawer}
            initial="collapsed"
            animate={drawerOpen ? 'expanded' : 'collapsed'}
            variants={drawerVariants}
          >
            <div
              className={styles.drawerHandle}
              onClick={() => setDrawerOpen(!drawerOpen)}
            >
              <div className={styles.handleBar} />
            </div>

            {drawerOpen && (
              <motion.div
                className={styles.drawerContent}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <div className={styles.drawerTitle}>Generate a New Course</div>
                <div className={styles.form}>
                  <div className={styles.formGroup}>
                    <label className={styles.label}>What do you want to learn?</label>
                    <input
                      type="text"
                      className={styles.input}
                      placeholder="e.g., Python for beginners, Advanced Java..."
                      value={courseTopic}
                      onChange={(e) => setCourseTopic(e.target.value)}
                    />
                  </div>
                  <div className={styles.formRow}>
                    <div className={styles.formGroupHalf}>
                      <label className={styles.label}>Duration</label>
                      <select
                        className={styles.select}
                        value={courseWeeks}
                        onChange={(e) => setCourseWeeks(e.target.value)}
                      >
                        <option value="1">1 week</option>
                        <option value="2">2 weeks</option>
                        <option value="3">3 weeks</option>
                        <option value="4">4 weeks</option>
                        <option value="6">6 weeks</option>
                        <option value="8">8 weeks</option>
                      </select>
                    </div>
                    <div className={styles.formGroupHalf}>
                      <label className={styles.label}>Skill Level</label>
                      <select
                        className={styles.select}
                        value={courseLevel}
                        onChange={(e) => setCourseLevel(e.target.value as any)}
                      >
                        <option value="Beginner">Beginner</option>
                        <option value="Intermediate">Intermediate</option>
                        <option value="Advanced">Advanced</option>
                      </select>
                    </div>
                  </div>
                  <button
                    className={styles.generateBtn}
                    onClick={handleGenerateCourse}
                    disabled={!courseTopic.trim() || isGeneratingCourse}
                  >
                    {isGeneratingCourse ? (
                      <>
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        >
                          ⏳
                        </motion.span>
                        Generating...
                      </>
                    ) : (
                      <>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                        </svg>
                        Generate Course
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading Overlay for Course Generation */}
      <AnimatePresence>
        {isGeneratingCourse && (
          <motion.div
            className={styles.loadingOverlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className={styles.loadingSpinner}
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <p className={styles.loadingText}>Creating your personalized course...</p>
            <div className={styles.loadingSteps}>
              {loadingMessages.map((msg, index) => (
                <p
                  key={index}
                  className={`${styles.loadingStep} ${index === loadingStep ? styles.active : ''}`}
                >
                  {msg}
                </p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Bar */}
      <div className={styles.inputBar}>
        {activeCourse && (
          <div className={styles.activeCourse}>
            Chatting in: <span className={styles.activeCourseName}>{activeCourse.courseName}</span>
          </div>
        )}
        <div className={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            placeholder="Ask a question or type your doubt..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSending || isGeneratingCourse}
            rows={1}
          />
          <button
            className={styles.sendBtn}
            onClick={handleSend}
            disabled={!input.trim() || isSending || isGeneratingCourse}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
