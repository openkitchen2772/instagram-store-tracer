import { randomUUID } from "node:crypto";
import StorebookPage from "@/components/StorebookPage";

export default function Home() {
  return <StorebookPage sessionUuid={randomUUID()} />;
}
