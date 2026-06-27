import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = (process.env.BACKEND_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function handleProxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");
  const url = new URL(req.url);
  const targetUrl = `${BACKEND_URL}/api/${pathStr}${url.search}`;

  const headers = new Headers();
  
  // Copy essential request headers
  req.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "host") {
      headers.set(key, value);
    }
  });
  
  // Set the host header for the target backend
  headers.set("host", new URL(BACKEND_URL).host);

  try {
    let body: any = undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      body = await req.text();
    }

    const response = await fetch(targetUrl, {
      method: req.method,
      headers: headers,
      body: body,
      cache: "no-store",
    });

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      // Skip headers that should be managed by Next.js or are modified during fetch decompression
      if (
        lowerKey !== "content-encoding" &&
        lowerKey !== "transfer-encoding" &&
        lowerKey !== "content-length" &&
        lowerKey !== "connection" &&
        lowerKey !== "keep-alive"
      ) {
        responseHeaders.set(key, value);
      }
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: any) {
    console.error(`[Proxy Error] Failed to fetch from backend at ${targetUrl}:`, error);
    return new Response(
      JSON.stringify({ detail: `The backend service could not be reached or timed out: ${error.message}` }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

export async function GET(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, context);
}

export async function POST(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, context);
}

export async function PUT(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, context);
}

export async function DELETE(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, context);
}
