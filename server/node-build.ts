import path from "path";
import { createServer } from "./index";
import express from "express";
import { port as configuredPort } from "./config/env";
import { quantProxy } from "./quantProxy";

// Supported local production topology (I10):
//   browser -> Express (127.0.0.1:PORT) -> /api/v1/* relayed untouched -> Python API (QUANT_API_URL)
//                                       -> other /api/* -> Express routes ; everything else -> built SPA
// The relay is mounted first: createServer() installs express.json(), which would consume POST bodies.
const app = express();
app.use("/api/v1", quantProxy());
app.use(createServer());
const port = configuredPort;

// In production, serve the built SPA files
const __dirname = import.meta.dirname;
const distPath = path.join(__dirname, "../spa");

// Serve static files
app.use(express.static(distPath));

// Handle React Router - serve index.html for all non-API routes
// Express 5 (path-to-regexp 8) no longer accepts "*": use a named wildcard.
app.get("/{*splat}", (req, res) => {
  // Don't serve index.html for API routes
  if (req.path.startsWith("/api/") || req.path.startsWith("/health")) {
    return res.status(404).json({ error: "API endpoint not found" });
  }

  res.sendFile(path.join(distPath, "index.html"));
});

// Local only by default; set HOST explicitly to expose the server.
app.listen(Number(port), process.env.HOST ?? "127.0.0.1", () => {
  console.log(`🚀 Fusion Starter server running on port ${port}`);
  console.log(`📱 Frontend: http://localhost:${port}`);
  console.log(`🔧 API: http://localhost:${port}/api`);
});

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("🛑 Received SIGTERM, shutting down gracefully");
  process.exit(0);
});

process.on("SIGINT", () => {
  console.log("🛑 Received SIGINT, shutting down gracefully");
  process.exit(0);
});
