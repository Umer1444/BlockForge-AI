import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ConfirmModal from "./ConfirmModal";

describe("ConfirmModal", () => {
    it("does not render when isOpen is false", () => {
        const { container } = render(
            <ConfirmModal
                isOpen={false}
                title="Test Title"
                message="Test Message"
                onConfirm={vi.fn()}
                onCancel={vi.fn()}
            />
        );
        expect(container.firstChild).toBeNull();
    });

    it("renders title, message, and buttons when isOpen is true", () => {
        render(
            <ConfirmModal
                isOpen={true}
                title="Prune History"
                message="Are you sure you want to prune?"
                onConfirm={vi.fn()}
                onCancel={vi.fn()}
            />
        );

        expect(screen.getByText("Prune History")).toBeInTheDocument();
        expect(screen.getByText("Are you sure you want to prune?")).toBeInTheDocument();
        expect(screen.getByText("CONFIRM")).toBeInTheDocument();
        expect(screen.getByText("CANCEL")).toBeInTheDocument();
    });

    it("calls onConfirm when confirm button is clicked", () => {
        const onConfirm = vi.fn();
        render(
            <ConfirmModal
                isOpen={true}
                title="Prune History"
                message="Are you sure?"
                confirmText="YES PRUNE"
                onConfirm={onConfirm}
                onCancel={vi.fn()}
            />
        );

        fireEvent.click(screen.getByText("YES PRUNE"));
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it("calls onCancel when cancel button or close icon is clicked", () => {
        const onCancel = vi.fn();
        render(
            <ConfirmModal
                isOpen={true}
                title="Prune History"
                message="Are you sure?"
                cancelText="GO BACK"
                onConfirm={vi.fn()}
                onCancel={onCancel}
            />
        );

        fireEvent.click(screen.getByText("GO BACK"));
        expect(onCancel).toHaveBeenCalledTimes(1);
    });
});
