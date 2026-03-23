'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/lib/store';
import type { Course, Day } from '@/types';
import styles from './page.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } }
};

const slideDown = {
  hidden: { height: 0, opacity: 0 },
  visible: { height: 'auto', opacity: 1, transition: { duration: 0.3 } }
};

export default function ProgressPage() {
  const router = useRouter();
  const { user } = useUser();
  const { courses, activeCourseId, setActiveCourse, getCourseProgress, getCourseAverageScore, getCourseCompletedDays, isCertificateEarned } = useAppStore();
  
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(activeCourseId);
  const [expandedWeeks, setExpandedWeeks] = useState<Set<number>>(new Set([1]));

  const selectedCourse = courses.find(c => c.id === selectedCourseId);

  useEffect(() => {
    if (!selectedCourseId && courses.length > 0) {
      setSelectedCourseId(courses[0].id);
    }
  }, [courses, selectedCourseId]);

  const toggleWeek = (weekNum: number) => {
    const newExpanded = new Set(expandedWeeks);
    if (newExpanded.has(weekNum)) {
      newExpanded.delete(weekNum);
    } else {
      newExpanded.add(weekNum);
    }
    setExpandedWeeks(newExpanded);
  };

  const getCourseColor = (index: number) => {
    const colors = ['#6c63ff', '#ff6b9d', '#4ade80', '#fbbf24', '#f87171', '#38bdf8'];
    return colors[index % colors.length];
  };

  const getDayStatus = (day: Day, dayIndex: number, weekIndex: number, course: Course): 'completed' | 'current' | 'locked' => {
    if (day.isCompleted) return 'completed';
    
    // Check if this is the first day
    if (weekIndex === 0 && dayIndex === 0) return 'current';
    
    // Check if previous day is completed
    let prevDay: Day | null = null;
    
    if (dayIndex > 0) {
      prevDay = course.weeks[weekIndex].days[dayIndex - 1];
    } else if (weekIndex > 0) {
      const prevWeek = course.weeks[weekIndex - 1];
      prevDay = prevWeek.days[prevWeek.days.length - 1];
    }
    
    if (prevDay && prevDay.isCompleted) return 'current';
    
    return 'locked';
  };

  const handleViewDay = (courseId: string, weekNum: number, dayNum: number) => {
    router.push(`/course/${courseId}/week-${weekNum}/day-${dayNum}`);
  };

  const progress = selectedCourseId ? getCourseProgress(selectedCourseId) : 0;
  const avgScore = selectedCourseId ? getCourseAverageScore(selectedCourseId) : 0;
  const completedDays = selectedCourseId ? getCourseCompletedDays(selectedCourseId) : { completed: 0, total: 0 };
  const certificateEarned = selectedCourseId ? isCertificateEarned(selectedCourseId) : false;

  const circumference = 2 * Math.PI * 54;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  if (courses.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📚</div>
          <h2 className={styles.emptyTitle}>No courses yet</h2>
          <p className={styles.emptyText}>
            Start by generating your first course. Our AI will create a personalized learning path for you.
          </p>
          <button 
            className={styles.emptyBtn}
            onClick={() => router.push('/dashboard')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Create Your First Course
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Course Progress</h1>
        <div className={styles.courseTabs}>
          {courses.map((course, index) => (
            <button
              key={course.id}
              className={`${styles.courseTab} ${selectedCourseId === course.id ? styles.active : ''}`}
              onClick={() => setSelectedCourseId(course.id)}
            >
              <span 
                className={styles.courseDot} 
                style={{ background: getCourseColor(index) }}
              />
              {course.courseName}
            </button>
          ))}
          <button
            className={`${styles.courseTab} ${styles.newCourseTab}`}
            onClick={() => router.push('/dashboard')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Course
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.content}>
          {selectedCourse && (
            <motion.div
              initial="hidden"
              animate="visible"
              variants={fadeUp}
            >
              {selectedCourse.weeks.map((week, weekIndex) => {
                    const completedDaysInWeek = week.days.filter(d => d.isCompleted).length;
                    const isExpanded = expandedWeeks.has(week.weekNumber);
                    
                    return (
                      <div key={week.weekNumber} className={styles.weekAccordion}>
                        <button
                          className={`${styles.weekHeader} ${isExpanded ? styles.expanded : ''}`}
                          onClick={() => toggleWeek(week.weekNumber)}
                        >
                          <div className={styles.weekInfo}>
                            <span className={styles.weekNumber}>Week {week.weekNumber}</span>
                            <span className={styles.weekTitle}>{week.weekTitle}</span>
                            <span className={styles.weekProgress}>
                              {completedDaysInWeek}/{week.days.length} days
                            </span>
                          </div>
                          <svg
                            className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <path d="M6 9l6 6 6-6" />
                          </svg>
                        </button>

                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              className={styles.daysList}
                              initial="hidden"
                              animate="visible"
                              exit="hidden"
                              variants={slideDown}
                            >
                              {week.days.map((day, dayIndex) => {
                                const status = getDayStatus(day, dayIndex, weekIndex, selectedCourse);
                                const isLocked = status === 'locked';
                                
                                return (
                                  <motion.div
                                    key={day.dayNumber}
                                    className={styles.dayCard}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: dayIndex * 0.05 }}
                                  >
                                    <div className={`${styles.dayStatus} ${styles[status]}`}>
                                      {status === 'completed' && '✓'}
                                      {status === 'current' && '🔓'}
                                      {status === 'locked' && '🔒'}
                                    </div>
                                    <div className={styles.dayInfo}>
                                      <div className={styles.dayTitle}>
                                        Day {day.dayNumber}: {day.dayTitle}
                                      </div>
                                      <div className={styles.dayTopics}>
                                        {day.topics.slice(0, 3).join(' • ')}
                                      </div>
                                    </div>
                                    <div className={styles.dayActions}>
                                      {isLocked ? (
                                        <span className={styles.lockedLabel}>
                                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                                          </svg>
                                          Locked
                                        </span>
                                      ) : (
                                        <button
                                          className={styles.viewBtn}
                                          onClick={() => handleViewDay(selectedCourse.id, week.weekNumber, day.dayNumber)}
                                        >
                                          View
                                        </button>
                                      )}
                                      {day.quizScore !== undefined && (
                                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                          {day.quizScore}%
                                        </span>
                                      )}
                                    </div>
                                  </motion.div>
                                );
                              })}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
            </motion.div>
          )}
        </div>

        <aside className={styles.sidebar}>
          <div className={styles.progressCard}>
            <h3 className={styles.progressTitle}>Your Progress</h3>
            <div className={styles.progressRing}>
              <div className={styles.ringContainer}>
                <svg className={styles.ringSvg} width="140" height="140">
                  <circle
                    className={styles.ringBg}
                    cx="70"
                    cy="70"
                    r="54"
                  />
                  <motion.circle
                    className={styles.ringProgress}
                    cx="70"
                    cy="70"
                    r="54"
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset }}
                  />
                </svg>
                <div className={styles.ringText}>
                  <span className={styles.ringPercentage}>{progress}%</span>
                  <span className={styles.ringLabel}>Complete</span>
                </div>
              </div>
            </div>
            <div className={styles.progressStats}>
              <div className={styles.stat}>
                <div className={styles.statValue}>{completedDays.completed}/{completedDays.total}</div>
                <div className={styles.statLabel}>Days Completed</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.statValue}>{avgScore}%</div>
                <div className={styles.statLabel}>Avg Score</div>
              </div>
            </div>
          </div>

          <div className={styles.progressCard}>
            <h3 className={styles.progressTitle}>Day Checklist</h3>
            <div className={styles.checklist}>
              {selectedCourse?.weeks.map(week => (
                <div key={week.weekNumber} className={styles.weekChecklist}>
                  <div className={styles.weekChecklistTitle}>Week {week.weekNumber}</div>
                  <div className={styles.dayChecks}>
                    {week.days.map(day => (
                      <div
                        key={day.dayNumber}
                        className={`${styles.dayCheck} ${day.isCompleted ? styles.completed : ''}`}
                        title={`Day ${day.dayNumber}: ${day.dayTitle}`}
                      >
                        {day.isCompleted ? '✓' : day.dayNumber}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.certificateCard}>
            <div className={styles.certificateIcon}>
              {certificateEarned ? '🏆' : '📜'}
            </div>
            <h3 className={styles.certificateTitle}>Certificate</h3>
            <p className={`${styles.certificateStatus} ${certificateEarned ? styles.unlocked : ''}`}>
              {certificateEarned 
                ? 'Congratulations! You earned your certificate!' 
                : 'Complete all days with 50%+ average score to unlock'}
            </p>

            {certificateEarned && selectedCourse && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <div className={styles.certificatePreview}>
                  <div className={styles.certificatePreviewName}>
                    {user?.firstName} {user?.lastName}
                  </div>
                  <div className={styles.certificatePreviewCourse}>
                    {selectedCourse.courseName}
                  </div>
                  <div className={styles.certificatePreviewDate}>
                    Completed on {new Date().toLocaleDateString()}
                  </div>
                </div>
                <button className={styles.downloadBtn}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download Certificate
                </button>
              </motion.div>
            )}

            {!certificateEarned && (
              <div className={styles.lockedIcon}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Locked
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}
