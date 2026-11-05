import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.string().optional(),
  MT5_WS_URL: z.string().url().optional(),
  MT5_API_KEY: z.string().optional(),
  PING_MESSAGE: z.string().optional(),
});

export type AppEnv = z.infer<typeof EnvSchema>;

export const env: AppEnv = EnvSchema.parse(process.env);

export const isDev = env.NODE_ENV !== "production";
export const isProd = env.NODE_ENV === "production";
export const port = env.PORT ?? "3000";

