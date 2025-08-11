#!/usr/bin/env python3
"""
Load testing for HawkFish API.

This script runs basic load tests to ensure the API can handle
concurrent requests and meets performance targets.
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any, List

import httpx
import pytest


@dataclass
class LoadTestResult:
    """Results from a load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    errors: List[str]


class LoadTester:
    """Load testing helper for HawkFish API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self.session_token: str | None = None
    
    async def setup(self) -> None:
        """Set up test session."""
        async with httpx.AsyncClient() as client:
            # Login to get session token
            response = await client.post(
                f"{self.base_url}/redfish/v1/SessionService/Sessions",
                json={"UserName": "local", "Password": ""}
            )
            if response.status_code == 200:
                self.session_token = response.json()["SessionToken"]
    
    def auth_headers(self) -> dict[str, str]:
        """Get headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["X-Auth-Token"] = self.session_token
        return headers
    
    async def make_request(self, method: str, path: str, **kwargs) -> tuple[int, float]:
        """Make a single request and return status code and response time."""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self.auth_headers(),
                    timeout=30.0,
                    **kwargs
                )
                duration_ms = (time.time() - start_time) * 1000
                return response.status_code, duration_ms
            except Exception:
                duration_ms = (time.time() - start_time) * 1000
                return 0, duration_ms  # 0 indicates error
    
    async def run_concurrent_requests(
        self,
        method: str,
        path: str,
        num_requests: int,
        concurrency: int = 10,
        **request_kwargs
    ) -> LoadTestResult:
        """Run concurrent requests and collect metrics."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request():
            async with semaphore:
                return await self.make_request(method, path, **request_kwargs)
        
        start_time = time.time()
        
        # Run all requests concurrently
        tasks = [bounded_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration_seconds = end_time - start_time
        
        # Analyze results
        successful_requests = 0
        failed_requests = 0
        response_times = []
        errors = []
        
        for status_code, response_time_ms in results:
            if status_code >= 200 and status_code < 400:
                successful_requests += 1
            else:
                failed_requests += 1
                if status_code == 0:
                    errors.append("Request timeout/error")
                else:
                    errors.append(f"HTTP {status_code}")
            
            response_times.append(response_time_ms)
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if response_times else 0  # 95th percentile
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if response_times else 0  # 99th percentile
        requests_per_second = num_requests / duration_seconds if duration_seconds > 0 else 0
        
        return LoadTestResult(
            total_requests=num_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            duration_seconds=duration_seconds,
            requests_per_second=requests_per_second,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            errors=list(set(errors))  # Unique errors
        )


@pytest.mark.asyncio
@pytest.mark.performance
async def test_service_root_load():
    """Test service root endpoint under load."""
    tester = LoadTester()
    await tester.setup()
    
    result = await tester.run_concurrent_requests(
        "GET", "/redfish/v1/", num_requests=100, concurrency=10
    )
    
    print(f"\n=== Service Root Load Test ===")
    print(f"Total requests: {result.total_requests}")
    print(f"Successful: {result.successful_requests}")
    print(f"Failed: {result.failed_requests}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"RPS: {result.requests_per_second:.1f}")
    print(f"Avg response time: {result.avg_response_time_ms:.1f}ms")
    print(f"95th percentile: {result.p95_response_time_ms:.1f}ms")
    print(f"99th percentile: {result.p99_response_time_ms:.1f}ms")
    
    # Performance assertions
    assert result.successful_requests >= result.total_requests * 0.95  # 95% success rate
    assert result.avg_response_time_ms < 200  # Average under 200ms
    assert result.p95_response_time_ms < 500  # 95th percentile under 500ms
    assert result.requests_per_second > 50  # At least 50 RPS


@pytest.mark.asyncio
@pytest.mark.performance
async def test_systems_list_load():
    """Test systems list endpoint under load."""
    tester = LoadTester()
    await tester.setup()
    
    result = await tester.run_concurrent_requests(
        "GET", "/redfish/v1/Systems", num_requests=50, concurrency=5
    )
    
    print(f"\n=== Systems List Load Test ===")
    print(f"Total requests: {result.total_requests}")
    print(f"Successful: {result.successful_requests}")
    print(f"Failed: {result.failed_requests}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"RPS: {result.requests_per_second:.1f}")
    print(f"Avg response time: {result.avg_response_time_ms:.1f}ms")
    print(f"95th percentile: {result.p95_response_time_ms:.1f}ms")
    
    # Systems endpoint may be slower due to libvirt calls
    assert result.successful_requests >= result.total_requests * 0.9  # 90% success rate
    assert result.avg_response_time_ms < 1000  # Average under 1 second
    assert result.p95_response_time_ms < 2000  # 95th percentile under 2 seconds


@pytest.mark.asyncio
@pytest.mark.performance
async def test_pagination_load():
    """Test paginated endpoints under load."""
    tester = LoadTester()
    await tester.setup()
    
    # Test different page sizes
    page_sizes = [10, 25, 50, 100]
    
    for page_size in page_sizes:
        result = await tester.run_concurrent_requests(
            "GET", 
            f"/redfish/v1/Systems?page=1&per_page={page_size}",
            num_requests=20,
            concurrency=5
        )
        
        print(f"\n=== Pagination Load Test (page_size={page_size}) ===")
        print(f"RPS: {result.requests_per_second:.1f}")
        print(f"Avg response time: {result.avg_response_time_ms:.1f}ms")
        
        # Pagination should be efficient
        assert result.successful_requests >= result.total_requests * 0.95
        assert result.avg_response_time_ms < 500


async def main():
    """Run performance tests manually."""
    print("🚀 HawkFish Performance Tests")
    print("=" * 40)
    
    tester = LoadTester()
    await tester.setup()
    
    # Service Root test
    print("\n1. Testing Service Root endpoint...")
    result1 = await tester.run_concurrent_requests(
        "GET", "/redfish/v1/", num_requests=100, concurrency=10
    )
    print(f"   ✓ {result1.requests_per_second:.1f} RPS, {result1.avg_response_time_ms:.1f}ms avg")
    
    # Systems list test
    print("2. Testing Systems list endpoint...")
    result2 = await tester.run_concurrent_requests(
        "GET", "/redfish/v1/Systems", num_requests=50, concurrency=5
    )
    print(f"   ✓ {result2.requests_per_second:.1f} RPS, {result2.avg_response_time_ms:.1f}ms avg")
    
    # Mixed workload test
    print("3. Testing mixed workload...")
    
    async def mixed_workload():
        endpoints = [
            "/redfish/v1/",
            "/redfish/v1/Systems",
            "/redfish/v1/Oem/HawkFish/Profiles",
            "/redfish/v1/Oem/HawkFish/Images",
        ]
        
        tasks = []
        for endpoint in endpoints:
            for _ in range(10):  # 10 requests per endpoint
                tasks.append(tester.make_request("GET", endpoint))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        successful = sum(1 for status, _ in results if 200 <= status < 400)
        avg_time = statistics.mean([t for _, t in results])
        
        return len(results), successful, duration, avg_time
    
    total, successful, duration, avg_time = await mixed_workload()
    rps = total / duration
    print(f"   ✓ {rps:.1f} RPS, {avg_time:.1f}ms avg, {successful}/{total} successful")
    
    print("\n✅ Performance tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
