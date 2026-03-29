// simulation/job_generator.js
// Usage: node job_generator.js <N> <lambda> <serviceModel>
// e.g. node job_generator.js 10000 1.5 exp
const fs = require('fs');

const N = parseInt(process.argv[2] || '10000', 10);
const lambda = parseFloat(process.argv[3] || '1.0'); // arrivals per unit time
const serviceModel = process.argv[4] || 'exp'; // exp | pareto | lognormal | uniform

// Helpers
function randUniform() { return Math.random(); }
function randExp(lambda){
  // inverse CDF
  return -Math.log(1 - randUniform()) / lambda;
}
function randPareto(xm = 1, alpha = 1.5){
  // Pareto with scale xm and shape alpha
  const u = randUniform();
  return xm / Math.pow(1 - u, 1/alpha);
}
function randLognormal(mu = 0, sigma = 1){
  // Box-Muller for normal then exp()
  const u1 = randUniform(), u2 = randUniform();
  const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return Math.exp(mu + sigma * z0);
}
function randTruncNormal(mu=1, sigma=0.5){
  let x = -1;
  while (x <= 0) {
    const u1 = randUniform(), u2 = randUniform();
    const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    x = mu + sigma * z0;
  }
  return x;
}

let arrival = 0;
const out = [];
for (let i=0;i<N;i++){
  const inter = randExp(lambda);
  arrival += inter;
  let service;
  if (serviceModel === 'exp') {
    service = randExp(1.0);            // mean=1
  } else if (serviceModel === 'pareto') {
    service = randPareto(0.5, 1.8);   // heavy tail
  } else if (serviceModel === 'lognormal') {
    service = randLognormal(0, 1);
  } else if (serviceModel === 'uniform'){
    service = 0.1 + Math.random()*2.0;
  } else { // default
    service = randExp(1.0);
  }
  out.push({
    job_id: i+1,
    arrival_time: arrival,
    interarrival: inter,
    service_time: service,
    model: serviceModel
  });
}

// Write CSV
const header = 'job_id,arrival_time,interarrival,service_time,model\n';
const csv = out.map(r => `${r.job_id},${r.arrival_time},${r.interarrival},${r.service_time},${r.model}`).join('\n');
fs.writeFileSync(`jobs_${serviceModel}_N${N}_lambda${lambda}.csv`, header + csv);
console.log('Wrote', `jobs_${serviceModel}_N${N}_lambda${lambda}.csv`);

// Example Run
//node simulation/job_generator.js 10000 1.5 exp
//node simulation/job_generator.js 10000 1.5 pareto
