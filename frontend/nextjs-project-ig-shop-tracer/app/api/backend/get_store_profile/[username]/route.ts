import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ username: string }> },
): Promise<NextResponse> {
  const { username } = await context.params;
  const normalizedUsername = username.trim();
  if (!normalizedUsername) {
    return NextResponse.json(
      { detail: "Username is required." },
      { status: 400 },
    );
  }

  const upstreamUrl = `${BACKEND_BASE_URL}/store_profile/${encodeURIComponent(normalizedUsername)}`;
  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Unable to reach backend service." },
      { status: 502 },
    );
  }

  const contentType = upstreamResponse.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return NextResponse.json(
      { detail: "Backend returned non-JSON response." },
      { status: 502 },
    );
  }

  let body: unknown;
  try {
    body = await upstreamResponse.json();
  } catch {
    return NextResponse.json(
      { detail: "Backend returned invalid JSON." },
      { status: 502 },
    );
  }

  return NextResponse.json(body, { status: upstreamResponse.status });
}
