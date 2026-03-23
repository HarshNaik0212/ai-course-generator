'use client';

import { motion } from 'framer-motion';
import styles from './HowItWorks.module.css';

const steps = [
  {
    number: 1,
    icon: '🚀',
    title: 'Generate Course',
    description: 'Tell us what you want to learn. Our AI creates a complete curriculum with daily lessons and quizzes.'
  },
  {
    number: 2,
    icon: '📚',
    title: 'Study Day by Day',
    description: 'Follow your personalized learning path. Complete lessons, take quizzes, and unlock new content.'
  },
  {
    number: 3,
    icon: '🎓',
    title: 'Earn Certificate',
    description: 'Complete all lessons and quizzes to earn your certificate. Share your achievement with the world.'
  }
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.2 } }
};

const connectorGrow = {
  hidden: { scaleX: 0 },
  visible: { scaleX: 1, transition: { duration: 0.8, ease: 'easeOut' as const } }
};

export default function HowItWorks() {
  return (
    <section id="how-it-works" className={styles.howItWorks}>
      <div className={styles.container}>
        <motion.div
          className={styles.sectionHeader}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={fadeUp}
        >
          <span className={styles.label}>How It Works</span>
          <h2 className={styles.title}>Your learning journey in 3 steps</h2>
        </motion.div>

        <div className={styles.steps}>
          <motion.div
            className={styles.connector}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={connectorGrow}
          >
            <div className={styles.connectorLine} />
          </motion.div>

          
          {steps.map((step, index) => (
            <motion.div
              key={index}
              className={styles.step}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-50px' }}
              variants={fadeUp}
            >
              <div className={styles.stepNumber}>
                <span className={styles.stepIcon}>{step.icon}</span>
              </div>
              <h3 className={styles.stepTitle}>{step.title}</h3>
              <p className={styles.stepDescription}>{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
