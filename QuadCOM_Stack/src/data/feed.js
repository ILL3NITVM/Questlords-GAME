/* Feed selector — THE seam. One boolean decides the world. */
import { MODE } from "../config.js";
import { createSimFeed } from "./simFeed.js";
import { createLiveFeed } from "./liveFeed.js";

export function createFeed(state) {
  return MODE.LIVE ? createLiveFeed(state) : createSimFeed(state);
}
