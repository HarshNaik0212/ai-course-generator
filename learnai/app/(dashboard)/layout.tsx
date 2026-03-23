'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/dashboard/Sidebar';
import ChatPanel from '@/components/chat/ChatPanel';
import styles from './layout.module.css';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [triggerNewCourse, setTriggerNewCourse] = useState(false);

  const handleNewCourse = () => {
    setTriggerNewCourse(prev => !prev);
  };

  const handleCourseGenerated = () => {
    setTriggerNewCourse(false);
  };

  return (
    <div className={styles.layout}>
      <motion.aside
        className={`${styles.sidebar} ${sidebarOpen ? styles.open : ''}`}
        initial={{ x: -280 }}
        animate={{ x: 0 }}
      >
        <Sidebar onNewCourse={handleNewCourse} />
      </motion.aside>

      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            className={`${styles.overlay} ${styles.open}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      <main className={styles.main}>
        {children || (
          <ChatPanel 
            onTriggerNewCourse={triggerNewCourse}
            onCourseGenerated={handleCourseGenerated}
          />
        )}
      </main>
    </div>
  );
}
