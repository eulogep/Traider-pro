import type { Request, RequestHandler } from "express";
import type { ZodSchema } from "zod";

export interface ValidatedRequest<T> extends Request {
  validatedBody: T;
}

export function validateBody<T>(schema: ZodSchema<T>): RequestHandler {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);

    if (!result.success) {
      return res.status(400).json({
        error: "Invalid request body",
        details: result.error.issues,
      });
    }

    (req as ValidatedRequest<T>).validatedBody = result.data;
    return next();
  };
}

