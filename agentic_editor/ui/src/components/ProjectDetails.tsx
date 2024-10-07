import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getProjects, updateProject } from '../api/api';

const ProjectDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<any>(null);

  useEffect(() => {
    const fetchProject = async () => {
      const response = await getProjects();
      const foundProject = response.data.find((p: any) => p.id === id);
      setProject(foundProject);
    };
    fetchProject();
  }, [id]);

  if (!project) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{project.name}</h1>
      <p className="mb-4">{project.description}</p>
      {/* Add more project details and editing functionality here */}
    </div>
  );
};

export default ProjectDetails;
