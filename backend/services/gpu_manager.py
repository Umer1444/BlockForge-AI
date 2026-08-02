"""
BlockForge AI – GPU Resource Manager
"""

import logging

import torch

from config import settings

logger = logging.getLogger("blockforge.gpu")


class GPUManager:
    """Manage GPU resources across the processing pipeline."""

    def __init__(self):
        self.cuda_available = torch.cuda.is_available()
        self.mps_available = (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        )

        if self.cuda_available:
            self.device_type = "cuda"
            self.current_device = self._validate_gpu_device(
                settings.GPU_DEVICE
            )
        elif self.mps_available:
            self.current_device = "mps"
            self.device_type = "mps"
        else:
            self.current_device = "cpu"
            self.device_type = "cpu"

    def _validate_gpu_device(self, configured_device: str) -> str:
        """
        Validate the configured CUDA device.

        Falls back to cuda:0 if the configured device is invalid.
        Falls back to CPU if no CUDA devices are available.
        """
        device_count = torch.cuda.device_count()

        if device_count == 0:
            logger.warning("CUDA is available but no GPU devices were detected. Falling back to CPU.")
            self.device_type = "cpu"
            return "cpu"

        try:
            if configured_device.startswith("cuda:"):
                device_index = int(configured_device.split(":")[1])
            elif configured_device == "cuda":
                device_index = 0
            else:
                raise ValueError

            if 0 <= device_index < device_count:
                return configured_device if configured_device != "cuda" else "cuda:0"

            logger.warning(
                f"Configured GPU device '{configured_device}' does not exist. "
                "Falling back to cuda:0."
            )
            return "cuda:0"

        except (ValueError, IndexError):
            logger.warning(
                f"Invalid GPU device '{configured_device}'. "
                "Falling back to cuda:0."
            )
            return "cuda:0"

    def get_info(self) -> dict:
        """Return GPU hardware information."""
        info = {
            "available": self.cuda_available or self.mps_available,
            "device": self.current_device,
            "device_type": self.device_type,
            "cuda_available": self.cuda_available,
            "mps_available": self.mps_available,
        }


        if self.cuda_available:
            try:
                info["device_count"] = torch.cuda.device_count()
                info["devices"] = []

                for i in range(info["device_count"]):
                    props = torch.cuda.get_device_properties(i)
                    allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
                    reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                    total = props.total_mem / (1024 ** 3)

                    info["devices"].append(
                        {
                            "index": i,
                            "name": props.name,
                            "total_memory_gb": round(total, 2),
                            "allocated_gb": round(allocated, 2),
                            "free_gb": round(total - reserved, 2),
                        }
                    )

            except Exception as e:
                logger.exception(f"Failed to retrieve GPU information: {e}")
                self.fallback_to_cpu()

                return {
                    "available": False,
                    "device": "cpu",
                    "device_type": "cpu",
                    "cuda_available": False,
                    "mps_available": self.mps_available,
                }

        elif self.mps_available:
            info["device_name"] = "Apple Silicon GPU (MPS)"
            # MPS doesn't expose memory info as easily as CUDA

        if self.cuda_available and self.device_type == "cuda":
            info["device_count"] = torch.cuda.device_count()
            info["devices"] = []

            for i in range(info["device_count"]):
                props = torch.cuda.get_device_properties(i)


                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                reserved = torch.cuda.memory_reserved(i) / (1024**3)
                total = props.total_mem / (1024**3)


                allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)


                try:
                    free_bytes, total_bytes = torch.cuda.mem_get_info(i)
                    free = free_bytes / (1024 ** 3)
                    total = total_bytes / (1024 ** 3)
                except (AttributeError, RuntimeError):
                    reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                    total = props.total_mem / (1024 ** 3)
                    free = total - reserved

                reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                total = props.total_mem / (1024 ** 3)


                info["devices"].append(
                    {
                        "index": i,
                        "name": props.name,
                        "total_memory_gb": round(total, 2),
                        "allocated_gb": round(allocated, 2),

                        "free_gb": round(free, 2),

                        "free_gb": round(total - reserved, 2),

                    }
                )

        elif self.mps_available:
            info["device_name"] = "Apple Silicon GPU (MPS)"


        return info

    def get_best_device(self) -> str:
        """Select the best available device."""
        if self.cuda_available and self.device_type == "cuda":
            return self.current_device
        if self.mps_available:
            return "mps"
        return "cpu"


    def check_memory(self, required_gb: float | None = None) -> bool:
        """
        Check if enough GPU memory is available.

        If required_gb is not provided, use the configured value from settings.
        """
        if not self.cuda_available:
            # For MPS/CPU we don't have a reliable memory check yet
            return True

        if required_gb is None:
            required_gb = settings.GPU_MEMORY_THRESHOLD_GB


    def check_memory(self, required_gb: float = 4.0) -> bool:
        """Check if enough GPU memory is available."""
        if not self.cuda_available or self.device_type != "cuda":
            return True



        try:
            device_idx = (
                int(self.current_device.split(":")[-1])
                if ":" in self.current_device
                else 0


        device_idx = (
            int(self.current_device.split(":")[-1])
            if ":" in self.current_device
            else 0
        )


        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(device_idx)
            free = free_bytes / (1024 ** 3)
            total = total_bytes / (1024 ** 3)
        except (AttributeError, RuntimeError):
            props = torch.cuda.get_device_properties(device_idx)
            reserved = torch.cuda.memory_reserved(device_idx) / (1024 ** 3)
            total = props.total_mem / (1024 ** 3)
            free = total - reserved

        props = torch.cuda.get_device_properties(device_idx)
        reserved = torch.cuda.memory_reserved(device_idx) / (1024**3)
        total = props.total_mem / (1024**3)
        free = total - reserved


        if free < required_gb:
            logger.warning(
                f"Low GPU memory: {free:.2f} GB free, "
                f"{required_gb:.2f} GB required"

            )

            props = torch.cuda.get_device_properties(device_idx)
            reserved = torch.cuda.memory_reserved(device_idx) / (1024 ** 3)
            total = props.total_mem / (1024 ** 3)
            free = total - reserved

            if free < required_gb:
                logger.warning(
                    f"Low GPU memory: {free:.2f} GB free, "
                    f"{required_gb:.2f} GB required"
                )
                return False

            return True

        except Exception as e:
            logger.exception(f"Failed to check GPU memory: {e}")
            self.fallback_to_cpu()
            return False


        return True


    def fallback_to_cpu(self):
        """Gracefully fallback to CPU when GPU is unavailable."""
        if self.current_device == "cpu":
            return

        logger.warning(f"Falling back from {self.device_type} to CPU")
        self.current_device = "cpu"
        self.device_type = "cpu"

    def try_gpu_or_fallback(self, required_gb: float | None = None) -> str:
        """
        Attempt to use GPU if available, otherwise fallback to CPU.


        If required_gb is not provided, the configured threshold is used.


        Returns:
            Device string to use.
        """
        if self.device_type == "cpu":
            return "cpu"


        if required_gb is None:
            required_gb = settings.GPU_MEMORY_THRESHOLD_GB

        if not self.check_memory(required_gb):
            logger.warning(
                f"Insufficient GPU memory "
                f"({required_gb:.2f} GB required), falling back to CPU"

        if not self.check_memory(required_gb):
            logger.warning(
                f"Insufficient GPU memory ({required_gb}GB required), "
                "falling back to CPU"

            )
            self.fallback_to_cpu()
            return "cpu"

        return self.current_device

    def clear_cache(self):
        """Clear GPU cache."""

        try:
            if self.cuda_available:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            elif self.mps_available:
                # MPS doesn't have an explicit clear_cache
                pass

            logger.debug(f"⛏  {self.device_type.upper()} cache cleared")

        except Exception as e:
            logger.exception(f"Failed to clear GPU cache: {e}")
            self.fallback_to_cpu()

        if self.cuda_available and self.device_type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        elif self.mps_available:


            pass

        logger.debug(f"⛏  {self.device_type.upper()} cache cleared")

            pass

        logger.debug(f"⛏ {self.device_type.upper()} cache cleared")


    def log_status(self):
        """Log current GPU status."""
        info = self.get_info()

        if not info["available"]:
            logger.info("⛏ No GPU available, using CPU")
            return

        if info["cuda_available"] and self.device_type == "cuda":
            for dev in info["devices"]:
                logger.info(
                    f"⛏ GPU {dev['index']}: {dev['name']} | "
                    f"{dev['free_gb']:.1f}/{dev['total_memory_gb']:.1f} GB free"
                )
        elif info["mps_available"]:
            logger.info("⛏ Using Apple Silicon GPU (MPS)")


# Singleton
gpu_manager = GPUManager()