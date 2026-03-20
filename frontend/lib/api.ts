/**
 * API utilities for Contract Review Assistant backend
 * 
 * Backend server: http://localhost:8000
 * 
 * CORS Configuration:
 * Make sure your FastAPI backend has CORS middleware configured to allow:
 * - Origins: http://localhost:3000, http://localhost:3001
 * - Methods: GET, POST
 * - Headers: Content-Type, Accept
 * 
 * Example CORS setup in FastAPI:
 * ```python
 * from fastapi.middleware.cors import CORSMiddleware
 * app.add_middleware(
 *   CORSMiddleware,
 *   allow_origins=["http://localhost:3000", "http://localhost:3001"],
 *   allow_credentials=True,
 *   allow_methods=["*"],
 *   allow_headers=["*"],
 * )
 * ```
 */

import { ContractAnalysis } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Analyze a contract file (PDF or DOCX)
 * @param file - The contract file to analyze
 * @returns Promise with complete contract analysis
 * @throws APIError if the request fails
 */
export async function analyzeContract(file: File): Promise<ContractAnalysis> {
  // Validate file type
  const allowedTypes = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
  if (!allowedTypes.includes(file.type)) {
    throw new APIError("Invalid file type. Please upload a PDF or DOCX file.", 400);
  }

  // Validate file size (10MB max)
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    throw new APIError("File too large. Maximum size is 10MB.", 400);
  }

  // Create FormData
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze-contract`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = "Failed to analyze contract";
      let errorDetails = "";

      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
        errorDetails = JSON.stringify(errorData);
      } catch {
        errorDetails = await response.text();
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (!data.analysis) {
      throw new APIError("Invalid response format from server", 500);
    }

    return data.analysis as ContractAnalysis;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    // Network or other errors
    if (error instanceof TypeError) {
      throw new APIError(
        "Cannot connect to backend server. Make sure it's running at " + API_BASE_URL,
        0,
        error.message
      );
    }

    throw new APIError(
      "An unexpected error occurred",
      500,
      error instanceof Error ? error.message : String(error)
    );
  }
}

/**
 * Check if the backend API is healthy
 * @returns Promise with boolean indicating health status
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
