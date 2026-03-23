'use client';

import { motion } from 'framer-motion';
import styles from './Testimonials.module.css';

const testimonials = [
  {
    content: "LearnAI helped me master Python in just 4 weeks. The AI-generated curriculum was perfectly structured for my learning pace.",
    name: "Alex Chen",
    role: "Software Engineer",
    avatar: "AC",
    rating: 5
  },
  {
    content: "The interactive quizzes and progress tracking kept me motivated throughout my machine learning course. Highly recommended!",
    name: "Sarah Miller",
    role: "Data Scientist",
    avatar: "SM",
    rating: 5
  },
  {
    content: "I earned my certificate in Web Development and landed my dream job. LearnAI made learning feel like a game!",
    name: "James Wilson",
    role: "Frontend Developer",
    avatar: "JW",
    rating: 5
  }
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } }
};

export default function Testimonials() {
  return (
    <section className={styles.testimonials}>
      <div className={styles.container}>
        <motion.div
          className={styles.sectionHeader}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={fadeUp}
        >
          <span className={styles.label}>Testimonials</span>
          <h2 className={styles.title}>Loved by learners worldwide</h2>
        </motion.div>

        <motion.div
          className={styles.grid}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
          variants={stagger}
        >
          {testimonials.map((testimonial, index) => (
            <motion.div key={index} className={styles.card} variants={fadeUp}>
              <div className={styles.rating}>
                {[...Array(testimonial.rating)].map((_, i) => (
                  <span key={i} className={styles.star}>★</span>
                ))}
              </div>
              <p className={styles.content}>"{testimonial.content}"</p>
              <div className={styles.author}>
                <div className={styles.avatar}>{testimonial.avatar}</div>
                <div className={styles.authorInfo}>
                  <span className={styles.name}>{testimonial.name}</span>
                  <span className={styles.role}>{testimonial.role}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
