// Safety guard: fail the Vercel build early if the backend URL was forgotten
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    "NEXT_PUBLIC_API_URL is not set. " +
    "Add it in Vercel -> Project Settings -> Environment Variables " +
    "and set it to your Render backend URL (e.g. https://studdy-buddy-api.onrender.com)"
  );
}

/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = nextConfig;
