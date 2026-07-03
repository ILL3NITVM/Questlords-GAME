/* Feed selector — THE seam. One boolean decides the world. */
import { MODE } from "../config.js";
import { createSimFeed } from "./simFeed.js";
import { createLiveFeed } from "./liveFeed.js";

export function createFeed(ctx) {
  return MODE.LIVE ? createLiveFeed(ctx) : createSimFeed(ctx);
}
