import { useState } from 'react';

function Enroll() {
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Student Enrollment</h1>

      <div className="bg-white shadow rounded-lg p-6">
        <div className="mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-2">Enroll New Student</h2>
          <p className="text-sm text-gray-500">
            Use the form below to enroll a new student. Upload 2-6 clear photos of the student's face for best results.
          </p>
        </div>

        <iframe
          src={`${API_BASE}/enroll`}
          className="w-full h-96 border border-gray-300 rounded"
          title="Enrollment Form"
        />

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-medium text-blue-900 mb-2">Tips for Best Results:</h3>
          <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
            <li>Use good lighting - avoid shadows on the face</li>
            <li>Capture photos from slightly different angles</li>
            <li>Ensure the face is clearly visible and not obstructed</li>
            <li>Upload 3-5 photos for optimal recognition accuracy</li>
            <li>Photos should be at least 200x200 pixels</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Enroll;