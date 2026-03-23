'use client';

import { motion } from 'framer-motion';
import styles from './Features.module.css';

const features = [
  {
    icon: '🎓',
    title: 'AI-Generated Courses',
    description: 'Transform any topic into a structured curriculum. Our AI creates week-by-week learning paths tailored to your goals.'
  },
  {
    icon: '📊',
    title: 'Progress Tracking',
    description: 'Track your learning journey with detailed progress indicators, completion rates, and performance analytics.'
  },
  {
    icon: '❓',
    title: 'Interactive Quizzes',
    description: 'Test your knowledge with AI-generated quizzes. Get instant feedback and track your scores over time.'
  },
  {
    icon: '💬',
    title: 'Conversation History',
    description: 'Chat with your AI tutor anytime. All conversations are saved so you can revisit explanations and examples.'
  },
  {
    icon: '🏆',
    title: 'Certificates',
    description: 'Earn certificates upon course completion. Share your achievements and showcase your new skills.'
  },
  {
    icon: '🎯',
    title: 'Personalized Learning',
    description: 'Learn at your own pace with content adapted to your skill level - beginner, intermediate, or advanced.'
  }
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } }
};

export default function Features() {
  return (
    <section id="features" className={styles.features}>
      <div className={styles.container}>
        <motion.div
          className={styles.sectionHeader}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={fadeUp}
        >
          <span className={styles.label}>Features</span>
          <h2 className={styles.title}>Everything you need to learn</h2>
          <p className={styles.subtitle}>
            Powerful features designed to make your learning journey effective and enjoyable.
          </p>
        </motion.div>

        <motion.div
          className={styles.grid}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
          variants={stagger}
        >
          {features.map((feature, index) => (
            <motion.div key={index} className={styles.card} variants={fadeUp}>
              <div className={styles.icon}>{feature.icon}</div>
              <h3 className={styles.cardTitle}>{feature.title}</h3>
              <p className={styles.cardDescription}>{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
