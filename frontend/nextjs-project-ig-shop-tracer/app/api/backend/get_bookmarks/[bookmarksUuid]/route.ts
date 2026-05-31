import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL;

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ bookmarksUuid: string }> },
): Promise<NextResponse> {
  const { bookmarksUuid } = await context.params;
  const normalizedUuid = bookmarksUuid.trim();
  if (!normalizedUuid) {
    return NextResponse.json(
      { success: false, message: "Bookmarks uuid is required." },
      { status: 400 },
    );
  }

  const upstreamUrl = `${BACKEND_BASE_URL}/get_bookmarks/${encodeURIComponent(normalizedUuid)}`;
  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
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
