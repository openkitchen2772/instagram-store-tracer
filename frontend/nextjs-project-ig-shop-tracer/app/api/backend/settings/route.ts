import { NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL;

export async function GET(): Promise<NextResponse> {
  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(`${BACKEND_BASE_URL}/settings`, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { message: "Unable to reach backend service." },
      { status: 502 },
    );
  }

  const contentType = upstreamResponse.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return NextResponse.json(
      { message: "Backend returned non-JSON response." },
      { status: 502 },
    );
  }

  let body: unknown;
  try {
    body = await upstreamResponse.json();
  } catch {
    return NextResponse.json(
      { message: "Backend returned invalid JSON." },
      { status: 502 },
    );
  }

  return NextResponse.json(body, { status: upstreamResponse.status });
}
