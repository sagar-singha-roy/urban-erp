import { signal } from '@angular/core';
import { CurrentSession } from '../models/impersonation.model';

/**
 * The live support session, kept outside dependency injection so the HTTP interceptor can read it
 * without depending on HttpClient itself.
 */
export const supportSession = signal<CurrentSession | null>(null);

/** Set when the signed-in user may open the Support Impersonation Hub. */
export const canUseSupportHub = signal(false);

/** The API's answer once a session has ended. The interceptor raises SUPPORT_SESSION_ENDED instead of signing the agent out. */
export const SESSION_ENDED_DETAIL = 'This support session has ended.';
export const SUPPORT_SESSION_ENDED = 'support-session-ended';
