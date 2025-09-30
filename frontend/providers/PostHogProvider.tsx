'use client';

import { useEffect, Suspense } from 'react';
import { usePathname } from 'next/navigation';
import { initPostHog, trackPageView } from '../utils/analytics';

function PostHogPageView() {
  const pathname = usePathname();

  useEffect(() => {
    // Track page views on route changes
    if (pathname) {
      trackPageView(pathname);
    }
  }, [pathname]);

  return null;
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize PostHog on mount
    initPostHog();
  }, []);

  return (
    <>
      <Suspense fallback={null}>
        <PostHogPageView />
      </Suspense>
      {children}
    </>
  );
}
