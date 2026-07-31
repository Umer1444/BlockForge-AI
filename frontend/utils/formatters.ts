export const formatFileSize = (fileSize?: number): string => {
    if (!fileSize) {
        return "Unknown size";
    }

    return `${(fileSize / (1024 * 1024)).toFixed(1)} MB`;
};

export const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleDateString();
};