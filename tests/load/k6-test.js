import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 10 },
    { duration: '20s', target: 20 },
    { duration: '5s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const response = http.get(__ENV.QA_URL || 'http://k3s-server:30081');
  check(response, {
    'status es 200': (res) => res.status === 200,
  });
  sleep(1);
}