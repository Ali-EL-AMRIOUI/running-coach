import { z } from "zod";

export const PlanSchema = z.object({
  // Identity & History
  age: z.coerce.number().min(16).max(99),
  gender: z.enum(["M", "F"]),
  age_start: z.coerce.number().optional(),
  years_practice: z.coerce.number().optional(),
  other_sports: z.string().optional(),

  // Records (format hh:mm:ss ou mm:ss ou ss selon le cas)
  record_400m: z.string().optional(),
  record_800m: z.string().optional(),
  record_1500m: z.string().optional(),
  record_5000m: z.string().optional(),
  record_10000m: z.string().optional(),
  record_half: z.string().regex(/^\d{1,2}:\d{2}:\d{2}$/, "Format: hh:mm:ss").optional(),
  record_marathon: z.string().optional(),

  // Training Load
  current_volume: z.coerce.number().min(1),
  current_frequency: z.coerce.number().min(1),
  volume_s4: z.coerce.number().optional(),
  volume_s3: z.coerce.number().optional(),
  volume_s2: z.coerce.number().optional(),
  volume_s1: z.coerce.number().optional(),
  last_week_training: z.string().optional(),

  // Goal
  goal_distance: z.enum(["5k", "10k", "half", "marathon"]),
  goal_time: z.string().optional(),
  goal_date: z.string().min(1, "Date requise"),
  availability: z.coerce.number().min(1).max(7),
  double_session: z.enum(["yes", "no"]),
  double_session_days: z.string().optional(),

  // Health
  last_injury: z.string().optional(),
  return_date: z.string().optional(),
});

export type PlanFormData = z.infer<typeof PlanSchema>;