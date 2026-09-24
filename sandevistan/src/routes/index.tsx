import { createFileRoute } from "@tanstack/react-router";
import { DeskApp } from "@/desk/DeskApp";

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  return <DeskApp />;
}
