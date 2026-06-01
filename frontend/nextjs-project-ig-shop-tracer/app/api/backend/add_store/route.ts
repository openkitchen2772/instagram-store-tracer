import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_BASE_URL;

export async function POST(request: NextRequest): Promise<NextResponse> {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { success: false, message: "Invalid JSON request body." },
      { status: 400 },
    );
  }

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(`${BACKEND_BASE_URL}/add_store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { success: false, message: "Unable to reach backend service." },
      { status: 502 },
    );
  }

  const contentType = upstreamResponse.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return NextResponse.json(
      { success: false, message: "Backend returned non-JSON response." },
      { status: 502 },
    );
  }

  let body: unknown;
  try {
    body = await upstreamResponse.json();
  } catch {
    return NextResponse.json(
      { success: false, message: "Backend returned invalid JSON." },
      { status: 502 },
    );
  }

  return NextResponse.json(body, { status: upstreamResponse.status });
}
