import { http } from "@/lib/http";

interface Envelope<T> {
  success: boolean;
  data: T;
}

async function unwrap<T>(
  promise: Promise<{ data: Envelope<T> }>,
): Promise<T> {
  const res = await promise;
  return res.data.data;
}

export function listAuthoringJobs() {
  return unwrap<unknown[]>(http.get("/api/admin/fusion/authoring-jobs"));
}

export function listReviewCandidates() {
  return unwrap<unknown[]>(http.get("/api/admin/fusion/review-candidates"));
}

export function listSourceBundles() {
  return unwrap<unknown[]>(http.get("/api/admin/fusion/source-bundles"));
}
