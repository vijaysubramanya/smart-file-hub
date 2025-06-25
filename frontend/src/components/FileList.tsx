import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fileService, FileResponse, StorageSavings } from '../services/api';
import { formatBytes } from '../utils/format';
import { useAuth } from '../contexts/AuthContext';

interface FilterState {
  minSize: string;
  maxSize: string;
  type: string;
  dateFrom: string;
  dateTo: string;
}

const initialFilters: FilterState = {
  minSize: '',
  maxSize: '',
  type: '',
  dateFrom: '',
  dateTo: ''
};

export const FileList: React.FC = () => {
  const [files, setFiles] = useState<FileResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [uniqueTypes, setUniqueTypes] = useState<string[]>([]);
  const [storageSavings, setStorageSavings] = useState<StorageSavings | null>(null);
  const [showSavings, setShowSavings] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await fileService.list(currentPage, searchQuery, filters);
      setFiles(response.results);
      setTotalPages(response.pages);
      setIsSuperuser(response.is_superuser);
      
      // Extract unique file types
      const types = new Set(response.results.map(file => file.content_type));
      setUniqueTypes(Array.from(types));
    } catch (err) {
      setError('Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const loadStorageSavings = async () => {
    try {
      const savings = await fileService.getStorageSavings();
      setStorageSavings(savings);
      setShowSavings(true);
    } catch (err) {
      setError('Failed to load storage savings');
    }
  };

  useEffect(() => {
    loadFiles();
  }, [currentPage, searchQuery, filters]);

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters(initialFilters);
    setCurrentPage(1);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      await fileService.upload(file);
      loadFiles();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to upload file');
    }
  };

  const handleDownload = async (id: string, fileName: string) => {
    try {
      const blob = await fileService.download(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to download file');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) return;

    try {
      await fileService.delete(id);
      loadFiles();
    } catch (err) {
      setError('Failed to delete file');
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      setError('Failed to logout');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

    return (
    <div>
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">File Hub</h1>
              <p className="mt-1 text-sm text-gray-500">
                {isSuperuser ? 'Authorized Access' : 'Manage your files'}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8 space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search by filename..."
                className="w-full px-4 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
      </div>
            <div className="flex items-center space-x-4 ml-4">
              <button
                onClick={loadStorageSavings}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                See Storage Savings
              </button>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                {showFilters ? 'Hide Filters' : 'Show Filters'}
              </button>
              <label className="inline-block px-4 py-2 bg-indigo-600 text-white rounded-lg cursor-pointer hover:bg-indigo-700">
                Upload File
                <input
                  type="file"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </div>

          {/* Storage Savings Modal */}
          {showSavings && storageSavings && (
            <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
              <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div className="mt-3 text-center">
                  <h3 className="text-lg leading-6 font-medium text-gray-900">Storage Savings</h3>
                  <div className="mt-2 px-7 py-3">
                    <p className="text-sm text-gray-500">
                      Total storage saved through deduplication:
                    </p>
                    <p className="text-lg font-semibold text-indigo-600 mt-2">
                      {storageSavings.human_readable_saved}
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                      Number of duplicate files: {storageSavings.duplicate_count}
                    </p>
                  </div>
                  <div className="items-center px-4 py-3">
                    <button
                      onClick={() => setShowSavings(false)}
                      className="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filters Panel */}
          {showFilters && (
            <div className="bg-white p-4 rounded-lg shadow space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">File Size (bytes)</label>
                  <div className="flex space-x-2">
                    <input
                      type="number"
                      placeholder="Min size"
                      className="w-full px-3 py-2 border rounded-md"
                      value={filters.minSize}
                      onChange={(e) => handleFilterChange('minSize', e.target.value)}
                    />
                    <input
                      type="number"
                      placeholder="Max size"
                      className="w-full px-3 py-2 border rounded-md"
                      value={filters.maxSize}
                      onChange={(e) => handleFilterChange('maxSize', e.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">File Type</label>
                  <select
                    className="w-full px-3 py-2 border rounded-md"
                    value={filters.type}
                    onChange={(e) => handleFilterChange('type', e.target.value)}
                  >
                    <option value="">All Types</option>
                    {uniqueTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Upload Date</label>
                  <div className="flex space-x-2">
                    <input
                      type="date"
                      className="w-full px-3 py-2 border rounded-md"
                      value={filters.dateFrom}
                      onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                    />
                    <input
                      type="date"
                      className="w-full px-3 py-2 border rounded-md"
                      value={filters.dateTo}
                      onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
            <p className="mt-2 text-sm text-gray-500">Loading files...</p>
          </div>
        ) : (
          <>
            <div className="bg-white shadow overflow-hidden sm:rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Upload Date
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {files.map((file) => (
                    <tr key={file.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {file.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {formatBytes(file.size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {file.content_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {file.is_original ? (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            Original
                          </span>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                            Duplicate
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {formatDate(file.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleDownload(file.id, file.name)}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Download
                        </button>
                        <button
                          onClick={() => handleDelete(file.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-4 py-2 border rounded-lg disabled:opacity-50"
              >
                Previous
              </button>
              <span>
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-4 py-2 border rounded-lg disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}; 