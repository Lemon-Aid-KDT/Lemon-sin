import { create } from 'zustand';
import type { User } from 'firebase/auth';
import { onAuthChange, syncEmailToProfile } from '@/services/auth';
import { subscribeUserProfile } from '@/services/userProfile';
import { isFirebaseConfigured } from '@/config/firebase';
import type { UserProfile, UserRole } from '@/types/auth';

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  initialized: boolean;
  loading: boolean;
  profileUnsub: (() => void) | null;
  authUnsub: (() => void) | null;

  init: () => void;
  cleanup: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  initialized: false,
  loading: false,
  profileUnsub: null,
  authUnsub: null,

  init: () => {
    if (get().authUnsub) return; // 중복 구독 방지

    if (!isFirebaseConfigured()) {
      set({ initialized: true });
      return;
    }

    const authUnsub = onAuthChange((user) => {
      // 이전 프로필 구독 해제
      const prevProfileUnsub = get().profileUnsub;
      if (prevProfileUnsub) prevProfileUnsub();

      if (!user) {
        set({
          user: null,
          profile: null,
          profileUnsub: null,
          initialized: true,
        });
        return;
      }

      // 익명 사용자는 프로필을 구독하지 않는다
      if (user.isAnonymous) {
        set({ user, profile: null, profileUnsub: null, initialized: true });
        return;
      }

      const profileUnsub = subscribeUserProfile(user.uid, (profile) => {
        // 프로필이 존재할 때만 이메일 동기화 — 존재하지 않으면 signUp* 플로우가
        // ensureUserProfile로 완전한 프로필을 생성하도록 맡긴다. (race condition 방지)
        if (profile) {
          void syncEmailToProfile(user, profile.email ?? null).catch(() => {});
        }
        set({ profile, initialized: true });
      });
      set({ user, profileUnsub, initialized: true });
    });

    set({ authUnsub });
  },

  cleanup: () => {
    const { authUnsub, profileUnsub } = get();
    if (authUnsub) authUnsub();
    if (profileUnsub) profileUnsub();
    set({ authUnsub: null, profileUnsub: null });
  },

  setLoading: (loading) => set({ loading }),
}));

// --- 셀렉터 ---

export const selectIsAuthenticated = (s: AuthState): boolean =>
  !!s.user && !s.user.isAnonymous;

export const selectRole = (s: AuthState): UserRole | null =>
  s.profile?.role ?? null;

export const selectIsStaff = (s: AuthState): boolean =>
  s.profile?.role === 'staff' || s.profile?.role === 'admin';

export const selectIsAdmin = (s: AuthState): boolean =>
  s.profile?.role === 'admin';

export const selectIsSuspended = (s: AuthState): boolean =>
  s.profile?.status === 'suspended' || s.profile?.status === 'deleted';
