export type OnceSchedule = { kind: "once"; at: string };
export type Schedule = OnceSchedule;
export type Job = { id: string; name: string; schedule: Schedule };
