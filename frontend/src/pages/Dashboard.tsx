import { Container, Typography, Box } from '@mui/material'

function Dashboard() {
  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          ElasticSeer Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Autonomous Remediation Platform
        </Typography>
      </Box>
    </Container>
  )
}

export default Dashboard
