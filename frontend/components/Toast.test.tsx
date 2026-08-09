import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Toast from "./Toast";

describe("Toast", () => {
    it("does not render when message is null", () => {
        const { container } = render(
            <Toast message={null} onClose={vi.fn()} />
        );
        expect(container.firstChild).toBeNull();
    });

    it("renders message and icon when message is provided", () => {
        render(
            <Toast message="Failed to delete job" type="error" onClose={vi.fn()} />
        );

        expect(screen.getByText("Failed to delete job")).toBeInTheDocument();
        expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("calls onClose when close button is clicked", () => {
        const onClose = vi.fn();
        render(
            <Toast message="Operation failed" onClose={onClose} />
        );

        fireEvent.click(screen.getByLabelText("Dismiss notification"));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
