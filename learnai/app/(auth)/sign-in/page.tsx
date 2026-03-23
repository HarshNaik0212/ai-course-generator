'use client';

import { SignIn } from '@clerk/nextjs';
import { motion } from 'framer-motion';
import Link from 'next/link';
import styles from './page.module.css';

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

export default function SignInPage() {
  return (
    <div className={styles.container}>
      <div className={styles.background}>
        <motion.div
          className={`${styles.orb} ${styles.orb1}`}
          animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className={`${styles.orb} ${styles.orb2}`}
          animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.3, 0.2] }}
          transition={{ duration: 10, repeat: Infinity }}
        />
      </div>

      <motion.div
        className={styles.content}
        initial="hidden"
        animate="visible"
        variants={fadeIn}
      >
        <div className={styles.branding}>
          <Link href="/" className={styles.logo}>
            <div className={styles.logoIcon}>🧠</div>
            LearnAI
          </Link>
          <p className={styles.tagline}>Welcome back! Sign in to continue learning.</p>
        </div>

        <div className={styles.card}>
          <div className={styles.clerkWrapper}>
            <SignIn 
              appearance={{
                elements: {
                  rootBox: 'clerk-root',
                  card: 'clerk-card',
                  formButtonPrimary: 'clerk-button-primary'
                }
              }}
              routing="path"
              path="/sign-in"
              forceRedirectUrl="/dashboard"
            />
          </div>
        </div>

        <Link href="/" className={styles.backLink}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Back to home
        </Link>
      </motion.div>
    </div>
  );
}
