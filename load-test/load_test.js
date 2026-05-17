import http from 'k6/http';
import { sleep, check } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

// Simulates Black Friday: ramp to 500 virtual users
export const options = {
    stages: [
        { duration: '30s', target: 10 },
        { duration: '1m',  target: 100 },
        { duration: '2m',  target: 500 },
        { duration: '1m',  target: 100 },
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'],
        errors: ['rate<0.5'],
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';

export default function () {
    const endpoints = [
        `${BASE_URL}/`,
        `${BASE_URL}/products`,
        `${BASE_URL}/health`,
    ];

    if (Math.random() < 0.1) {
        endpoints.push(`${BASE_URL}/checkout`);
    }

    const url = endpoints[Math.floor(Math.random() * endpoints.length)];
    const res = http.get(url);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time OK': (r) => r.timings.duration < 2000,
    });

    errorRate.add(res.status !== 200);
    sleep(0.1);
}
