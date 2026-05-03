import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const rawUrl = request.nextUrl.searchParams.get("url");
  if (!rawUrl) {
    return NextResponse.json({ message: "Missing url query parameter." }, { status: 400 });
  }

  let targetUrl: URL;
  try {
    targetUrl = new URL(rawUrl);
  } catch {
    return NextResponse.json({ message: "Invalid image url." }, { status: 400 });
  }

  if (targetUrl.protocol !== "http:" && targetUrl.protocol !== "https:") {
    return NextResponse.json({ message: "Only http/https image urls are allowed." }, { status: 400 });
  }

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(targetUrl.toString(), {
      method: "GET",
      redirect: "follow",
      headers: {
        "User-Agent": "IG-Shop-Tracer-Image-Proxy/1.0",
      },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ message: "Failed to fetch remote image." }, { status: 502 });
  }

  if (!upstreamResponse.ok || !upstreamResponse.body) {
    return NextResponse.json(
      { message: `Failed to fetch remote image (status ${upstreamResponse.status}).` },
      { status: 502 },
    );
  }

  const contentType = upstreamResponse.headers.get("content-type") ?? "application/octet-stream";
  return new NextResponse(upstreamResponse.body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
    },
  });
}
