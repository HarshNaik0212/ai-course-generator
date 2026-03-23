'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import styles from './Hero.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } }
};

const floatOrb = {
  animate: {
    y: [0, -20, 0],
    transition: {
      duration: 6,
      repeat: Infinity,
      ease: 'easeInOut' as const
    }
  }
};

export default function Hero() {
  return (
    <section className={styles.hero}>
      <div className={styles.background}>
        <motion.div
          className={`${styles.orb} ${styles.orb1}`}
          animate={{ y: [0, -30, 0], x: [0, 20, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className={`${styles.orb} ${styles.orb2}`}
          animate={{ y: [0, 20, 0], x: [0, -30, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className={`${styles.orb} ${styles.orb3}`}
          animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <motion.div
        className={styles.content}
        initial="hidden"
        animate="visible"
        variants={stagger}
      >
        <div className={styles.textContent}>
          <motion.span className={styles.badge} variants={fadeUp}>
            ✨ Powered by AI
          </motion.span>
          
          <motion.h1 className={styles.headline} variants={fadeUp}>
            Learn Anything.{' '}
            <span className={styles.highlight}>Master Everything.</span>
          </motion.h1>
          
          <motion.p className={styles.subheadline} variants={fadeUp}>
            Transform any topic into a personalized learning journey. Our AI creates 
            structured courses, tracks your progress, and helps you master new skills 
            day by day.
          </motion.p>
          
          <motion.div className={styles.ctaButtons} variants={fadeUp}>
            <Link href="/sign-up" className={styles.primaryBtn}>
              Start Learning Free
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </Link>
            <button className={styles.secondaryBtn}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Watch Demo
            </button>
          </motion.div>
        </div>

        <motion.div className={styles.visual} variants={fadeUp}>
          <div className={styles.dashboardMockup}>
            <div className={styles.mockupHeader}>
              <span className={`${styles.mockupDot} ${styles.mockupDotRed}`} />
              <span className={`${styles.mockupDot} ${styles.mockupDotYellow}`} />
              <span className={`${styles.mockupDot} ${styles.mockupDotGreen}`} />
            </div>
            <div className={styles.mockupContent}>
              <div className={styles.mockupSidebar}>
                <div className={styles.mockupSidebarItem} />
                <div className={styles.mockupSidebarItem} />
                <div className={styles.mockupSidebarItem} />
              </div>
              <div className={styles.mockupChat}>
                <div className={`${styles.mockupMessage} ${styles.mockupMessageAI}`}>
                  Ready to learn Python? Let's start!
                </div>
                <div className={`${styles.mockupMessage} ${styles.mockupMessageUser}`}>
                  Generate a Python course for me
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
