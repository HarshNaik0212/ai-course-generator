'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import styles from './CTA.module.css';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

export default function CTA() {
  return (
    <section className={styles.cta}>
      <div className={styles.background}>
        <motion.div
          className={`${styles.orb} ${styles.orb1}`}
          animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className={`${styles.orb} ${styles.orb2}`}
          animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 10, repeat: Infinity }}
        />
      </div>

      <motion.div
        className={styles.container}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-100px' }}
        variants={fadeUp}
      >
        <h2 className={styles.title}>Ready to Start Learning?</h2>
        <p className={styles.subtitle}>
          Join thousands of learners who are mastering new skills with AI-powered courses.
        </p>
        <Link href="/sign-up" className={styles.button}>
          Get Started Free
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </Link>
      </motion.div>
    </section>
  );
}
