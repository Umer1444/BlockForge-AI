import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryCard, { HistoryItem } from "./HistoryCard";

const apiUrl = "http://localhost:8000";

const baseItem: HistoryItem = {
  id: "1",
  job_id: "job-1",
  filename: "test-video.mp4",
  state: "completed",
  progress: 100,
  preview_url: "/preview/test-video.jpg",
  thumbnail_url: "/thumbnails/test-video.jpg",
  output_ready: true,
  output_url: "/output/test-video.mp4",
  created_at: 1710000000,
  width: 1920,
  height: 1080,
  resolution: "1080p",
  orientation: "landscape",
  fps: 30,
  duration: 12.5,
  file_size: 10 * 1024 * 1024,
};

describe("HistoryCard", () => {
  const onClick = vi.fn();
  const onDownload = vi.fn();
  const onDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a completed video", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.getByText("test-video.mp4")).toBeInTheDocument();
    expect(screen.getByText("1080p")).toBeInTheDocument();
    expect(screen.getByText("landscape")).toBeInTheDocument();
    expect(screen.getByTitle("Download Video")).toBeInTheDocument();
  });

  it("renders a processing video without a download button", () => {
    const item = {
      ...baseItem,
      state: "processing",
      output_url: undefined,
    };

    render(
      <HistoryCard
        item={item}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.queryByTitle("Download Video")).not.toBeInTheDocument();
  });

  it("renders a failed video without a download button", () => {
    const item = {
      ...baseItem,
      state: "failed",
      output_url: undefined,
    };

    render(
      <HistoryCard
        item={item}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.queryByTitle("Download Video")).not.toBeInTheDocument();
  });

  it("renders the thumbnail when thumbnail_url exists", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    const image = screen.getByAltText("test-video.mp4");

    expect(image).toHaveAttribute(
      "src",
      `${apiUrl}/thumbnails/test-video.jpg`
    );
  });

  it("falls back to preview_url when thumbnail_url is missing", () => {
    const item = {
      ...baseItem,
      thumbnail_url: undefined,
    };

    render(
      <HistoryCard
        item={item}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.getByAltText("test-video.mp4")).toHaveAttribute(
      "src",
      `${apiUrl}/preview/test-video.jpg`
    );
  });

  it("shows the download button only for completed videos with output_url", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.getByTitle("Download Video")).toBeInTheDocument();
  });

  it("renders the delete button when onDelete is provided", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        onDelete={onDelete}
        apiUrl={apiUrl}
      />
    );

    expect(screen.getByTitle("Delete from Server")).toBeInTheDocument();
  });

  it("does not render the delete button without onDelete", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(
      screen.queryByTitle("Delete from Server")
    ).not.toBeInTheDocument();
  });

  it("calls onClick with the item when the card is clicked", () => {
    const { container } = render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    fireEvent.click(container.firstElementChild!);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(baseItem);
  });

  it("calls onDownload with the event and item", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    fireEvent.click(screen.getByTitle("Download Video"));

    expect(onDownload).toHaveBeenCalledTimes(1);
    expect(onDownload.mock.calls[0][1]).toBe(baseItem);
  });

  it("calls onDelete with the event and item", () => {
    render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        onDelete={onDelete}
        apiUrl={apiUrl}
      />
    );

    fireEvent.click(screen.getByTitle("Delete from Server"));

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onDelete.mock.calls[0][1]).toBe(baseItem);
  });

  it("applies active styling when isActive is true", () => {
    const { container } = render(
      <HistoryCard
        item={baseItem}
        onClick={onClick}
        onDownload={onDownload}
        isActive
        apiUrl={apiUrl}
      />
    );

    expect(container.firstElementChild).toHaveClass(
      "border-[var(--mc-emerald)]"
    );
  });

  it("renders fallback values for missing metadata", () => {
    const item: HistoryItem = {
      id: "2",
      job_id: "job-2",
      state: "processing",
      progress: 0,
      preview_url: "/preview/fallback.jpg",
      created_at: 1710000000,
    };

    render(
      <HistoryCard
        item={item}
        onClick={onClick}
        onDownload={onDownload}
        apiUrl={apiUrl}
      />
    );

    expect(screen.getByText("Unnamed Forge")).toBeInTheDocument();
    expect(screen.getByText("Unknown res")).toBeInTheDocument();
    expect(screen.getByText(/Unknown size/)).toBeInTheDocument();
    expect(screen.getByText(/0s/)).toBeInTheDocument();

    expect(screen.getByAltText("Video preview")).toHaveAttribute(
      "src",
      `${apiUrl}/preview/fallback.jpg`
    );
  });
});