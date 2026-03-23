'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import styles from './Navbar.module.css';

const fadeDown = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

export default function Navbar() {
  return (
    <motion.nav
      className={styles.navbar}
      initial="hidden"
      animate="visible"
      variants={fadeDown}
    >
      <Link href="/" className={styles.logo}>
        <div className={styles.logoIcon}>🧠</div>
        LearnAI
      </Link>

      <ul className={styles.navLinks}>
        <li>
          <a href="#features" className={styles.navLink}>Features</a>
        </li>
        <li>
          <a href="#how-it-works" className={styles.navLink}>How It Works</a>
        </li>
        <li>
          <a href="#pricing" className={styles.navLink}>Pricing</a>
        </li>
      </ul>

      <div className={styles.actions}>
        <Link href="/sign-in" className={styles.signInBtn}>
          Sign In
        </Link>
        <Link href="/sign-up" className={styles.getStartedBtn}>
          Get Started Free
        </Link>
        <button className={styles.mobileMenuBtn} aria-label="Menu">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>
    </motion.nav>
  );
}
