const jobs = new Map([
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

function get(id) {
  return jobs.get(id);
}

function create(name, schedule) {
  const job = { id: String(nextId++), name, schedule };
  jobs.set(job.id, job);
  return job;
}

function replace(job) {
  jobs.set(job.id, job);
  return job;
}

module.exports = { get, create, replace };
