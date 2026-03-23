import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in',
  '/sign-up',
  '/api/chat'
]);

const isProtectedRoute = createRouteMatcher([
  '/dashboard(.*)',
  '/progress(.*)',
  '/course(.*)'
]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|a?png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webp)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
