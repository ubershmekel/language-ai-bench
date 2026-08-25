import { Job, Schedule } from "./types";
const jobs = new Map<string, Job>([
  [
    "1",
    {
      id: "1",
      name: "backup",
      schedule: { kind: "once", at: "2030-01-01T00:00:00.000Z" },
    },
  ],
]);
let nextId = 2;
export function get(id: string): Job | undefined {
  return jobs.get(id);
}
export function create(name: string, schedule: Schedule): Job {
  const job = { id: String(nextId++), name, schedule };
  jobs.set(job.id, job);
  return job;
}
export function replace(job: Job): Job {
  jobs.set(job.id, job);
  return job;
}
