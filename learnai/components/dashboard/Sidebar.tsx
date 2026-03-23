'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser, useClerk } from '@clerk/nextjs';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import type { Course, ChatSession } from '@/types';
import styles from './Sidebar.module.css';

const slideIn = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.2 } }
};

const dropdownVariants = {
  hidden: { opacity: 0, y: -10, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.15 } }
};

interface SidebarProps {
  onNewCourse: () => void;
}

export default function Sidebar({ onNewCourse }: SidebarProps) {
  const { user } = useUser();
  const { signOut } = useClerk();
  const router = useRouter();
  
  const { courses, chatSessions, activeCourseId, activeChatSessionId, setActiveCourse, setActiveChatSession, addChatSession } = useAppStore();
  
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedCourses, setExpandedCourses] = useState<Set<string>>(new Set());

  const toggleCourse = (courseId: string) => {
    const newExpanded = new Set(expandedCourses);
    if (newExpanded.has(courseId)) {
      newExpanded.delete(courseId);
    } else {
      newExpanded.add(courseId);
    }
    setExpandedCourses(newExpanded);
  };

  const handleNewChat = (courseId: string) => {
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      courseId,
      title: 'New Chat',
      createdAt: new Date().toISOString(),
      messages: []
    };
    addChatSession(newSession);
    setActiveChatSession(newSession.id);
    setActiveCourse(courseId);
  };

  const handleSelectChat = (sessionId: string, courseId: string) => {
    setActiveChatSession(sessionId);
    setActiveCourse(courseId);
  };

  const getCourseColor = (index: number) => {
    const colors = ['#6c63ff', '#ff6b9d', '#4ade80', '#fbbf24', '#f87171', '#38bdf8'];
    return colors[index % colors.length];
  };

  const getUserInitials = () => {
    if (!user) return '?';
    const firstName = user.firstName || '';
    const lastName = user.lastName || '';
    return (firstName[0] + lastName[0]).toUpperCase() || user.emailAddresses[0]?.emailAddress[0].toUpperCase() || '?';
  };

  const getSessionsForCourse = (courseId: string) => {
    return chatSessions.filter(s => s.courseId === courseId);
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.userSection}>
        <div 
          className={styles.userInfo}
          onClick={() => setUserMenuOpen(!userMenuOpen)}
        >
          <div className={styles.userAvatar}>{getUserInitials()}</div>
          <div className={styles.userDetails}>
            <div className={styles.userName}>
              {user?.firstName} {user?.lastName}
            </div>
            <div className={styles.userEmail}>
              {user?.emailAddresses[0]?.emailAddress}
            </div>
          </div>
          <svg 
            className={`${styles.dropdownIcon} ${userMenuOpen ? styles.open : ''}`}
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>

        <AnimatePresence>
          {userMenuOpen && (
            <motion.div
              className={styles.userMenu}
              initial="hidden"
              animate="visible"
              exit="hidden"
              variants={dropdownVariants}
            >
              <button className={styles.menuItem}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Profile
              </button>
              <button className={styles.menuItem}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Settings
              </button>
              <button 
                className={`${styles.menuItem} ${styles.menuItemDanger}`}
                onClick={() => signOut(() => router.push('/'))}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Sign Out
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className={styles.conversationsSection}>
        <div className={styles.sectionTitle}>Conversations</div>
        
        {courses.length === 0 ? (
          <div className={styles.emptyState}>
            <p className={styles.emptyText}>No courses yet. Create your first course to start learning!</p>
          </div>
        ) : (
          courses.map((course, index) => (
            <motion.div
              key={course.id}
              className={styles.courseFolder}
              initial="hidden"
              animate="visible"
              variants={slideIn}
            >
              <button
                className={styles.folderHeader}
                onClick={() => toggleCourse(course.id)}
              >
                <div 
                  className={styles.courseIcon}
                  style={{ background: getCourseColor(index) }}
                >
                  {course.courseName.charAt(0).toUpperCase()}
                </div>
                <span className={styles.courseName}>{course.courseName}</span>
                <svg
                  className={`${styles.expandIcon} ${expandedCourses.has(course.id) ? styles.expanded : ''}`}
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </button>

              <AnimatePresence>
                {expandedCourses.has(course.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className={styles.chatList}>
                      {getSessionsForCourse(course.id).map(session => (
                        <div
                          key={session.id}
                          className={`${styles.chatItem} ${activeChatSessionId === session.id ? styles.active : ''}`}
                          onClick={() => handleSelectChat(session.id, course.id)}
                        >
                          <span className={styles.chatTitle}>{session.title}</span>
                          <span className={styles.chatDate}>
                            {new Date(session.createdAt).toLocaleDateString()}
                          </span>
                        </div>
                      ))}
                      <button
                        className={styles.newChatBtn}
                        onClick={() => handleNewChat(course.id)}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="12" y1="5" x2="12" y2="19" />
                          <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                        New Chat
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))
        )}
      </div>

      <button className={styles.newCourseBtn} onClick={onNewCourse}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Create New Course
      </button>

      <Link href="/progress" className={styles.progressBtn}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
        Course Progress
      </Link>
    </aside>
  );
}
